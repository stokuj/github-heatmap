from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer


bearer_scheme = HTTPBearer(auto_error=False)


def extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Extract and validate a Bearer token from authorization credentials.

    Raises:
        HTTPException: If credentials are missing, malformed, or empty.
    """

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization Bearer token is required",
        )

    if credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise HTTPException(
            status_code=401,
            detail="Authorization Bearer token is required",
        )

    return credentials.credentials.strip()
