import logging
import re
from typing import Any, Dict, List, Union

from django.apps import apps
from django.db import OperationalError, ProgrammingError, connection
from openai import OpenAI

from core import settings

# ---------------------------
# Configuration
# ---------------------------
REPO_MODEL = "deepseek-chat"
DEEPSEEK_API_KEY: str = settings.DEEPSEEK_API_KEY  # type:ignore

# Initialize DeepSeek client
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

# Set up logging
logger = logging.getLogger(__name__)


# ---------------------------
# Schema Handling
# ---------------------------
def get_cached_schema() -> Dict[str, List[str]]:
    """Cache the schema of all models to include foreign key relationships."""
    schema = {}
    for model in apps.get_models():
        table_name = model._meta.db_table
        fields = []

        for field in model._meta.get_fields():
            if hasattr(field, "column"):
                fields.append(field.column)  # type:ignore
                if field.is_relation and hasattr(field, "attname"):
                    fields.append(field.attname)  # type:ignore

        schema[table_name] = fields
    return schema


# ---------------------------
# Input Sanitization
# ---------------------------
def sanitize_input(nl_query: str) -> str:
    """Sanitize the input to prevent SQL injection and remove harmful characters."""
    nl_query = re.sub(r"[;\"'\\]", "", nl_query)
    return nl_query.strip()


# ---------------------------
# SQL Syntax Validation
# ---------------------------
def contains_invalid_sql(sql: str) -> bool:
    """Check for placeholders or invalid syntax in the SQL query."""
    invalid_patterns = [r"\?", r"\:"]
    for pattern in invalid_patterns:
        if re.search(pattern, sql):
            return True
    return False


# ---------------------------
# Prompt Construction
# ---------------------------
def inject_schema_into_prompt(
    nl_query: str, schema: Dict[str, List[str]], tenant_schema: str
) -> str:
    """Construct the prompt for the LLM with schema and tenant context."""
    schema_str = "\n".join(
        [f"{table}: {', '.join(columns)}" for table, columns in schema.items()]
    )
    prompt = f"""
        You are a PostgreSQL expert. Generate a single PostgreSQL SELECT query for a tenant schema.
        Use ONLY these tables exactly as named. Do NOT invent table names.
        All table names must match the schema above.
        Do not add prefixes like 'tenant_' unless they exist in the schema.
        Please provide the SQL statement without any markdown, placeholders, or variables.

        Rules:
        1. Use only the tables and columns in the schema.
        2. Fully qualify tables using the tenant schema: {tenant_schema}.
        3. Use ILIKE for text comparisons.
        4. Return only one SELECT query. No multiple statements.
        5. Focus on human-readable columns instead of IDs.
        6. Do not use aliases.
        7. Include any tenant filtering in the query if needed.
        8. Do NOT use placeholders like ? or :variable. Use literal values or column names.
        9. Do NOT use PostgreSQL extensions or custom syntax.
        10. When joining any foreign key add _id to it meaning customer to order, use order.customer_id = customer.id

        Tenant schema: {tenant_schema}
        Schema:
        {schema_str}
        Question: {nl_query}
        SQL Query:
    """
    return prompt


# ---------------------------
# Clean SQL from Markdown
# ---------------------------
def clean_sql(sql: str) -> str:
    """Remove Markdown code fences and leading/trailing whitespace."""
    sql = re.sub(r"```sql|```", "", sql, flags=re.IGNORECASE)
    return sql.strip()


# ---------------------------
# PostgreSQL Query Execution
# ---------------------------
def execute_query(query: str, tenant_schema: str) -> List[Dict[str, Any]]:
    """Execute the SQL query and return the results."""
    if not is_valid_query(query):
        raise ValueError("Invalid or forbidden SQL detected")

    with connection.cursor() as cursor:
        cursor.execute(f'SET search_path TO "{tenant_schema}"')
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return results


def is_valid_query(query: str) -> bool:
    """Validate the SQL query to prevent dangerous operations."""
    forbidden_keywords = [
        "DELETE",
        "UPDATE",
        "DROP",
        "ALTER",
        "INSERT",
        "TRUNCATE",
        "CREATE",
    ]
    query_upper = query.upper()

    for keyword in forbidden_keywords:
        if re.search(rf"\b{keyword}\b", query_upper):
            raise ValueError(f"Forbidden SQL operation detected: {keyword}")

    if ";" in query.strip().rstrip(";"):
        raise ValueError("Multiple statements are not allowed.")

    if not query_upper.strip().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    return True


# ---------------------------
# LLM Interaction
# ---------------------------
def generate_llm_response(prompt: str) -> str | None:
    """Generate a response from the LLM (DeepSeek)."""
    response = client.chat.completions.create(
        model=REPO_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# ---------------------------
# Explain SQL Results
# ---------------------------
def explain_result(
    nl_query: str, sql_query: str, results: List[Dict[str, Any]]
) -> str | None:
    """Explain the SQL results in plain language."""
    results_str = "\n".join(str(r) for r in results) if results else "No results found"
    prompt_template = f"""
        You are an AI assistant. Explain the PostgreSQL SQL query results in plain language.
        do not use any SQL related words make it so that a layman can understand this and you can provide
        resposne in html snippet and not whole html
        and tailwindcss not markdown but 
        please make it in contrast that is most accesible 
                    
        Original Question: {nl_query}
        SQL Query: {sql_query}
        SQL Results: {results_str}
        Explanation:
    """
    if prompt_template:
        return generate_llm_response(prompt_template)


# ---------------------------
# Main Processing Function
# ---------------------------
def process_nl_query_for_tenant(
    nl_query: str, tenant: Any
) -> Dict[str, Union[str, List[Dict[str, Any]], None]]:
    """
    Process a natural language query for a tenant and return the SQL query, results, and explanation.
    """
    try:
        nl_query = sanitize_input(nl_query)
        schema = get_cached_schema()
        tenant_schema = tenant.schema_name

        prompt = inject_schema_into_prompt(nl_query, schema, tenant_schema)
        sql_query = generate_llm_response(prompt)
        sql_query = clean_sql(sql_query)
        sql_query = re.sub(r"\\([_])", r"\1", sql_query)  # Unescape underscores

        logger.info(f"Generated SQL: {sql_query}")

        # Reject queries with placeholders or invalid syntax
        if contains_invalid_sql(sql_query):
            raise ValueError("Generated SQL contains invalid placeholders or syntax.")

        results = execute_query(sql_query, tenant_schema)
        explanation = explain_result(nl_query, sql_query, results)

        return {
            "query": sql_query,
            "results": results,
            "explanation": explanation,
            "question": nl_query,
        }

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {
            "error": f"Validation error: {str(e)}",
            "query": sql_query if "sql_query" in locals() else None,
        }

    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Database error: {e}")
        return {
            "error": f"Database error: {str(e)}",
            "query": sql_query if "sql_query" in locals() else None,
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "query": sql_query if "sql_query" in locals() else None,
        }
