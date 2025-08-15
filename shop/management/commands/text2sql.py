# File: backoffice/management/commands/text2sql.py
# Create the directories: mkdir -p backoffice/management/commands/

import json

from django.core.management.base import BaseCommand

from shop.sql_utils import ask_db_chatbot, get_model_info


class Command(BaseCommand):
    help = "Text2SQL chatbot for natural language database queries"

    def add_arguments(self, parser):
        parser.add_argument(
            "question",
            nargs="?",
            type=str,
            help="Natural language question to convert to SQL",
        )
        parser.add_argument(
            "--info", action="store_true", help="Show database schema information"
        )
        parser.add_argument(
            "--interactive", action="store_true", help="Start interactive mode"
        )

    def handle(self, *args, **options):
        if options["info"]:
            self.show_info()
        elif options["interactive"]:
            self.interactive_mode()
        elif options["question"]:
            self.ask_question(options["question"])
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please provide a question or use --interactive mode"
                )
            )
            self.stdout.write('Usage: python manage.py text2sql "your question here"')
            self.stdout.write("       python manage.py text2sql --interactive")
            self.stdout.write("       python manage.py text2sql --info")

    def show_info(self):
        """Show database schema information"""
        self.stdout.write(self.style.SUCCESS("🔍 Database Schema Information"))
        self.stdout.write("=" * 50)

        info = get_model_info()
        self.stdout.write(f"📊 Total Models: {info['total_models']}")
        self.stdout.write(f"📱 Apps: {', '.join(info['apps'])}")
        self.stdout.write(f"🗄️  Tables: {', '.join(info['tables'])}")
        self.stdout.write(f"🤖 Model Loaded: {'Yes' if info['model_loaded'] else 'No'}")

    def ask_question(self, question):
        """Process a single question"""
        self.stdout.write(f"\n❓ Question: {question}")
        self.stdout.write("-" * 50)

        result = ask_db_chatbot(question)

        if result["success"]:
            self.stdout.write(self.style.SUCCESS("✅ Query executed successfully!"))
            self.stdout.write(f"🔍 SQL: {result['sql_query']}")
            self.stdout.write(f"📊 Results: {result['count']} records found")

            # Show first few results
            if result["results"]:
                self.stdout.write("\n📋 Sample Results:")
                for i, row in enumerate(result["results"][:5]):
                    self.stdout.write(f"  {i + 1}. {row}")

                if len(result["results"]) > 5:
                    remaining = len(result["results"]) - 5
                    self.stdout.write(f"  ... and {remaining} more records")
            else:
                self.stdout.write("  (No results)")

        else:
            self.stdout.write(self.style.ERROR(f"❌ Error: {result['error']}"))
            if result.get("sql_query"):
                self.stdout.write(f"Generated SQL: {result['sql_query']}")

    def interactive_mode(self):
        """Start interactive chatbot mode"""
        self.stdout.write(self.style.SUCCESS("🤖 Text2SQL Interactive Mode"))
        self.stdout.write("=" * 50)
        self.stdout.write('Type your questions or "quit" to exit')
        self.stdout.write('Commands: "info" - show schema, "help" - show help')
        self.stdout.write("=" * 50)

        while True:
            try:
                question = input("\n❓ Your question: ").strip()

                if question.lower() in ["quit", "exit", "q"]:
                    self.stdout.write("👋 Goodbye!")
                    break
                elif question.lower() == "info":
                    self.show_info()
                elif question.lower() == "help":
                    self.stdout.write("Available commands:")
                    self.stdout.write("  - Type any natural language question")
                    self.stdout.write("  - 'info' - show database schema")
                    self.stdout.write("  - 'quit' - exit")
                elif question:
                    self.ask_question(question)

            except (KeyboardInterrupt, EOFError):
                self.stdout.write("\n👋 Goodbye!")
                break
