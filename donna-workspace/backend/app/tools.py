import os

# Define a secure workspace sandbox folder path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../workspace"))


def ensure_workspace_exists():
    """Guarantees the mock storage sandbox directory exists."""
    if not os.path.exists(WORKSPACE_DIR):
        os.makedirs(WORKSPACE_DIR)
        # Create a sample business ledger document for testing
        mock_file = os.path.join(WORKSPACE_DIR, "june_ledger.txt")
        with open(mock_file, "w", encoding="utf-8") as f:
            f.write("TXN_10294: PENDING | AMOUNT: $4,500.00 | INVOICE MATCH: FALSE\n")
            f.write("TXN_10295: COMPLETED | AMOUNT: $1,250.00 | INVOICE MATCH: TRUE\n")


def safe_list_directory() -> list[str]:
    """MCP Adapter: Securely lists the names of target files inside the sandbox."""
    ensure_workspace_exists()
    try:
        return os.listdir(WORKSPACE_DIR)
    except Exception as e:
        return [f"Error scanning directories: {str(e)}"]


def safe_read_file(filename: str) -> str:
    """MCP Adapter: Validates context paths and reads document contents securely."""
    ensure_workspace_exists()
    # Canonicalize paths to block Directory Traversal attacks (../)
    target_path = os.path.abspath(os.path.join(WORKSPACE_DIR, filename))
    if not target_path.startswith(WORKSPACE_DIR):
        return "SECURITY EXCEPTION: Unauthorized file access path vector blocked."

    if not os.path.exists(target_path):
        return f"File target '{filename}' not found inside workspace."

    try:
        with open(target_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Failed to read file contents: {str(e)}"