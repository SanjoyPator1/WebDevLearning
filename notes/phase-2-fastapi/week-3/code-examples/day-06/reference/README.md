# Day 6: Response Handling & Response Models

This directory contains practical examples for **Day 6** of the FastAPI Mastery course. It focuses on controlling what data leaves your API, managing HTTP status codes, and handling different response types (JSON, HTML, Files).

## File Guide

| File                               | Topic                    | Key Concepts                                                                                 |
| ---------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------- |
| `01_response_model_basics.py`      | **Security & Filtering** | Why we need Response Models to filter sensitive data (e.g., passwords).                      |
| `02_response_model_parameters.py`  | **Model Configuration**  | Using `exclude_unset`, `exclude_none`, and `include/exclude` to clean up JSON output.        |
| `03_status_codes_and_errors.py`    | **HTTP Status Codes**    | Returning 201 (Created), 204 (No Content), and using Dynamic Status Codes (Response object). |
| `04_multiple_response_models.py`   | **Polymorphism**         | Using `Union` types to return different data shapes and documenting `responses={404: ...}`.  |
| `05_custom_response_types.py`      | **Non-JSON Responses**   | Returning `HTMLResponse`, `PlainTextResponse`, `RedirectResponse`, and custom Headers.       |
| `06_files_and_streaming.py`        | **Files & Streaming**    | How to handle file downloads (`FileResponse`) and data streaming (`StreamingResponse`).      |
| `07_complete_practical_example.py` | **Capstone**             | A realistic User Profile API combining computed fields, models, and error handling.          |

## How to Run

Navigate to the parent directory (one level up from `day-06`) and run the specific file using `uvicorn`.

**Example:**

```bash
# Run the basic response model example
uvicorn 01_response_model_basics:app --reload

# Run the streaming example
uvicorn 06_files_and_streaming:app --reload

```

## Key Takeaways

1. **Always use Response Models** for public endpoints to prevent data leaks.
2. Use **Computed Fields** (`@computed_field`) to calculate values (like tax or display names) at serialization time.
3. Use `StreamingResponse` for large datasets or files to save server memory.
4. Use proper **HTTP Status Codes** (201 for create, 204 for delete) to build standard APIs.
