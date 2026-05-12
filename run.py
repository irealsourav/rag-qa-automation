import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

app = typer.Typer(help="RAG QA Automation — CLI")
console = Console()


@app.command()
def ingest(
    source: str = typer.Argument(..., help="Source: jira | confluence | codebase | test_results | all"),
    project_key: str = typer.Option(None, help="Jira project key"),
    space_key: str = typer.Option(None, help="Confluence space key"),
    codebase_path: str = typer.Option(None, help="Path to test codebase"),
    results_path: str = typer.Option(None, help="Path to test result XML files"),
):
    """Ingest data into the vector store."""
    from pipeline.vectorstore import VectorStore
    from pipeline.chunker import TextChunker

    vs = VectorStore()
    chunker = TextChunker()

    sources = ["jira", "confluence", "codebase", "test_results"] if source == "all" else [source]

    for src in sources:
        console.print(f"[bold cyan]Ingesting:[/bold cyan] {src}")
        try:
            if src == "jira":
                from ingest.jira_loader import JiraLoader
                docs = JiraLoader().fetch_issues(project_key=project_key)
                vs.upsert(chunker.chunk_documents(docs), "requirements")

            elif src == "confluence":
                from ingest.confluence_loader import ConfluenceLoader
                docs = ConfluenceLoader().fetch_pages(space_key=space_key)
                vs.upsert(chunker.chunk_documents(docs), "requirements")

            elif src == "codebase":
                from ingest.codebase_loader import CodebaseLoader
                docs = CodebaseLoader(codebase_path).load_all()
                vs.upsert(chunker.chunk_documents(docs), "codebase")

            elif src == "test_results":
                from ingest.test_results_loader import TestResultsLoader
                docs = TestResultsLoader(results_path).load_all()
                vs.upsert(chunker.chunk_documents(docs), "test_results")

            console.print(f"[bold green]✓ Done:[/bold green] {src}")
        except Exception as e:
            console.print(f"[bold red]✗ Failed:[/bold red] {src} — {e}")


@app.command()
def generate(
    feature: str = typer.Argument(..., help="Feature or requirement to generate tests for"),
    framework: str = typer.Option("Cypress", help="Test framework"),
    count: int = typer.Option(5, help="Number of test cases"),
):
    """Generate test cases for a feature."""
    from pipeline.vectorstore import VectorStore
    from qa_outputs.test_generator import TestCaseGenerator

    console.print(Panel(f"Generating {count} test cases for: [bold]{feature}[/bold]", style="cyan"))
    result = TestCaseGenerator(VectorStore()).generate(feature, framework, count)
    console.print(Markdown(result))


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about the test codebase"),
):
    """Ask a question about the test codebase."""
    from pipeline.vectorstore import VectorStore
    from qa_outputs.codebase_qa import CodebaseQA

    console.print(Panel(f"Q: [bold]{question}[/bold]", style="blue"))
    answer = CodebaseQA(VectorStore()).ask(question)
    console.print(Markdown(answer))


@app.command()
def flaky(
    top_n: int = typer.Option(10, help="Number of flaky tests to analyse"),
):
    """Detect and analyse flaky tests."""
    from pipeline.vectorstore import VectorStore
    from qa_outputs.flaky_detector import FlakyTestDetector

    console.print(Panel("Analysing flaky tests...", style="yellow"))
    results = FlakyTestDetector(VectorStore()).detect_and_fix(top_n=top_n)
    if not results:
        console.print("[green]No flaky tests detected.[/green]")
        return
    for r in results:
        console.print(Panel(
            f"[bold]{r['test_name']}[/bold]\n"
            f"Flaky score: {r['flaky_score']:.0%}\n\n"
            f"{r['analysis']}",
            style="yellow",
        ))


@app.command()
def coverage(
    feature_area: str = typer.Option(None, help="Feature area to analyse (or all)"),
):
    """Analyse test coverage gaps."""
    from pipeline.vectorstore import VectorStore
    from qa_outputs.coverage_analyzer import CoverageAnalyzer

    console.print(Panel(f"Coverage analysis: {feature_area or 'all features'}", style="green"))
    analyzer = CoverageAnalyzer(VectorStore())
    report = analyzer.analyse(feature_area)
    untested = analyzer.get_untested_stories()
    console.print(Markdown(report))
    if untested:
        console.print(Panel(
            "\n".join(f"• {s}" for s in untested),
            title="Untested stories",
            style="red",
        ))


@app.command()
def serve():
    """Start the FastAPI server."""
    import uvicorn
    from config import config
    console.print(Panel(f"Starting API server at http://{config.API_HOST}:{config.API_PORT}", style="cyan"))
    uvicorn.run("api.main:app", host=config.API_HOST, port=config.API_PORT, reload=True)


if __name__ == "__main__":
    app()
