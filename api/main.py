from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from pipeline.vectorstore import VectorStore
from pipeline.chunker import TextChunker
from ingest.jira_loader import JiraLoader
from ingest.confluence_loader import ConfluenceLoader
from ingest.codebase_loader import CodebaseLoader
from ingest.test_results_loader import TestResultsLoader
from qa_outputs.test_generator import TestCaseGenerator
from qa_outputs.codebase_qa import CodebaseQA
from qa_outputs.flaky_detector import FlakyTestDetector
from qa_outputs.coverage_analyzer import CoverageAnalyzer
from config import config

app = FastAPI(
    title="RAG QA Automation API",
    description="AI-powered QA system — test generation, codebase Q&A, flaky detection, coverage analysis",
    version="1.0.0",
)

vectorstore = VectorStore()
chunker = TextChunker()
qa_chat = CodebaseQA(vectorstore)


class GenerateRequest(BaseModel):
    feature: str
    framework: Optional[str] = "Cypress"
    count: Optional[int] = 5
    include_negative: Optional[bool] = True


class AskRequest(BaseModel):
    question: str
    reset_history: Optional[bool] = False


class FlakyRequest(BaseModel):
    test_name: str
    error_message: Optional[str] = ""


class CoverageRequest(BaseModel):
    feature_area: Optional[str] = None


class IngestRequest(BaseModel):
    source: str
    project_key: Optional[str] = None
    space_key: Optional[str] = None
    codebase_path: Optional[str] = None
    results_path: Optional[str] = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "collections": {
            key: vectorstore.count(key)
            for key in ["requirements", "codebase", "test_results"]
        },
    }


@app.post("/generate-tests")
def generate_tests(req: GenerateRequest):
    try:
        generator = TestCaseGenerator(vectorstore)
        result = generator.generate(
            feature=req.feature,
            framework=req.framework,
            count=req.count,
            include_negative=req.include_negative,
        )
        return {"feature": req.feature, "test_cases": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask_codebase(req: AskRequest):
    try:
        if req.reset_history:
            qa_chat.reset_history()
        answer = qa_chat.ask(req.question)
        return {"question": req.question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-flaky")
def detect_flaky(req: FlakyRequest):
    try:
        detector = FlakyTestDetector(vectorstore)
        analysis = detector.analyse_single(req.test_name, req.error_message)
        return {"test_name": req.test_name, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/detect-flaky/all")
def detect_all_flaky(top_n: int = 10):
    try:
        detector = FlakyTestDetector(vectorstore)
        results = detector.detect_and_fix(top_n=top_n)
        return {"flaky_tests": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/coverage")
def analyse_coverage(req: CoverageRequest):
    try:
        analyzer = CoverageAnalyzer(vectorstore)
        report = analyzer.analyse(req.feature_area)
        untested = analyzer.get_untested_stories()
        return {
            "feature_area": req.feature_area or "all",
            "analysis": report,
            "untested_stories": untested,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_ingest, req)
    return {"status": "ingestion started", "source": req.source}


def _run_ingest(req: IngestRequest):
    try:
        if req.source == "jira":
            loader = JiraLoader()
            docs = loader.fetch_issues(project_key=req.project_key)
            chunks = chunker.chunk_documents(docs)
            vectorstore.upsert(chunks, collection_key="requirements")

        elif req.source == "confluence":
            loader = ConfluenceLoader()
            docs = loader.fetch_pages(space_key=req.space_key)
            chunks = chunker.chunk_documents(docs)
            vectorstore.upsert(chunks, collection_key="requirements")

        elif req.source == "codebase":
            loader = CodebaseLoader(req.codebase_path)
            docs = loader.load_all()
            chunks = chunker.chunk_documents(docs)
            vectorstore.upsert(chunks, collection_key="codebase")

        elif req.source == "test_results":
            loader = TestResultsLoader(req.results_path)
            docs = loader.load_all()
            chunks = chunker.chunk_documents(docs)
            vectorstore.upsert(chunks, collection_key="test_results")

        print(f"[Ingest] Completed: {req.source}")
    except Exception as e:
        print(f"[Ingest] Failed: {e}")


if __name__ == "__main__":
    uvicorn.run("api.main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
