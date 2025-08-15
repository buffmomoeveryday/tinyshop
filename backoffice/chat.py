# import json
# import os

# import django

# # Set your Django settings module
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
# django.setup()

# from django.apps import apps
# from django.db import connection
# from transformers import (
#     AutoModelForCausalLM,
#     AutoModelForSeq2SeqLM,
#     AutoTokenizer,
#     pipeline,
# )

# # 1️⃣ Load a smaller Text2SQL model from HuggingFace
# # Choose one of these smaller models (uncomment the one you want to use):

# # Option 1: T5-small (220M parameters) - Very lightweight, good for basic queries
# # model_name = "gaussalgo/T5-LM-Large-text2sql-spider"

# # Option 2: CodeT5-small (220M parameters) - Good balance of size and performance
# # model_name = "Salesforce/codet5-small-nq-en"

# # Option 3: FLAN-T5-small (80M parameters) - Smallest option, fastest loading
# model_name = "google/flan-t5-small"

# # Option 4: Another lightweight option specifically for Text2SQL
# # model_name = "juierror/flan-t5-text2sql-with-schema"

# tokenizer = AutoTokenizer.from_pretrained(model_name)

# # For T5-based models, use AutoModelForSeq2SeqLM

# model = AutoModelForSeq2SeqLM.from_pretrained(
#     model_name, torch_dtype="auto", device_map="auto"
# )

# # For seq2seq models, use text2text-generation pipeline
# nl2sql = pipeline("text2text-generation", model=model, tokenizer=tokenizer)


# # 2️⃣ Dynamically extract schema from Django models
# def get_django_schema():
#     schema_info = {}
#     for model in apps.get_models():
#         table_name = model._meta.db_table
#         fields = [field.name for field in model._meta.fields]
#         schema_info[table_name] = fields
#     return schema_info


# # 3️⃣ Enhanced chatbot function with better prompting
# def ask_db_chatbot(user_question):
#     schema_info = get_django_schema()

#     # Build a more specific prompt for the causal language model
#     prompt = f"""Given the following database schema:
#         {json.dumps(schema_info, indent=2)}

#         Convert this natural language question to SQL:
#         Question: {user_question}

#         SQL Query:"""

#     # Generate SQL with appropriate parameters for causal LM
#     response = nl2sql(
#         prompt,
#         max_new_tokens=150,  # Use max_new_tokens instead of max_length
#         do_sample=False,  # Use greedy decoding for consistency
#         temperature=0.1,  # Low temperature for more deterministic output
#         pad_token_id=tokenizer.eos_token_id,
#     )

#     # Extract the generated SQL (remove the original prompt)
#     full_response = response[0]["generated_text"]
#     sql_query = full_response[len(prompt) :].strip()

#     # Clean up the SQL query (remove any extra text after the SQL)
#     if ";" in sql_query:
#         sql_query = sql_query.split(";")[0] + ";"

#     print(f"Generated SQL: {sql_query}")

#     try:
#         # Execute SQL safely
#         with connection.cursor() as cursor:
#             cursor.execute(sql_query)
#             columns = [col[0] for col in cursor.description]
#             rows = cursor.fetchall()

#         # Return results as list of dicts
#         results = [dict(zip(columns, row)) for row in rows]
#         return {
#             "success": True,
#             "sql_query": sql_query,
#             "results": results,
#             "count": len(results),
#         }

#     except Exception as e:
#         return {
#             "success": False,
#             "sql_query": sql_query,
#             "error": str(e),
#             "results": [],
#         }


# # 4️⃣ Alternative function with better error handling and SQL validation
# def ask_db_chatbot_safe(user_question):
#     """
#     Enhanced version with better SQL validation and error handling
#     """

#     schema_info = get_django_schema()

#     # Create a more detailed schema description
#     schema_description = []
#     for table_name, fields in schema_info.items():
#         schema_description.append(f"Table {table_name}: {', '.join(fields)}")

#     prompt = f"""Database Schema:
# {chr(10).join(schema_description)}

# Question: {user_question}

# Generate a SELECT SQL query to answer this question:"""

#     try:
#         response = nl2sql(
#             prompt,
#             max_new_tokens=100,
#             do_sample=False,
#             temperature=0.1,
#             pad_token_id=tokenizer.eos_token_id,
#         )

#         full_response = response[0]["generated_text"]
#         sql_query = full_response[len(prompt) :].strip()

#         # Basic SQL validation - ensure it's a SELECT query
#         sql_query = sql_query.upper().strip()
#         if not sql_query.startswith("SELECT"):
#             return {
#                 "success": False,
#                 "error": "Generated query is not a SELECT statement",
#                 "sql_query": sql_query,
#                 "results": [],
#             }

#         # Remove any text after the first semicolon
#         if ";" in sql_query:
#             sql_query = sql_query.split(";")[0] + ";"

#         print(f"Generated SQL: {sql_query}")

#         # Execute the query
#         with connection.cursor() as cursor:
#             cursor.execute(sql_query)
#             columns = [col[0] for col in cursor.description]
#             rows = cursor.fetchall()

#         results = [dict(zip(columns, row)) for row in rows]

#         return {
#             "success": True,
#             "sql_query": sql_query,
#             "results": results,
#             "count": len(results),
#         }

#     except Exception as e:
#         return {
#             "success": False,
#             "error": f"Error: {str(e)}",
#             "sql_query": sql_query if "sql_query" in locals() else None,
#             "results": [],
#         }
