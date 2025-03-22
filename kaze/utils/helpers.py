import sqlite3
import contextlib
import time
from functools import wraps
import asyncio


@contextlib.contextmanager
def get_optimized_db_connection(db_path, timeout=20.0, read_only=False):
    """
    Get a database connection with optimized settings to reduce locking issues.

    Args:
        db_path: Path to the SQLite database
        timeout: Connection timeout in seconds
        read_only: Whether to open in read-only mode

    Yields:
        sqlite3.Connection: Configured SQLite connection
    """
    mode = sqlite3.SQLITE_OPEN_READONLY if read_only else sqlite3.SQLITE_OPEN_READWRITE

    for attempt in range(3):  # Try a few times to connect
        try:
            conn = sqlite3.connect(
                db_path,
                timeout=timeout,
                isolation_level=None
                if read_only
                else "IMMEDIATE",  # Auto-commit for read-only, immediate for writes
                detect_types=sqlite3.PARSE_DECLTYPES,
            )

            # Configure SQLite for better concurrency
            if not read_only:
                conn.execute(
                    "PRAGMA journal_mode=WAL"
                )  # Write-Ahead Logging for better concurrency
                conn.execute(
                    "PRAGMA synchronous=NORMAL"
                )  # Balance between safety and speed
                conn.execute("PRAGMA busy_timeout=10000")  # 10 seconds busy timeout
                conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
                conn.execute(
                    "PRAGMA cache_size=-10000"
                )  # Use larger cache (about 10MB)
                conn.execute(
                    "PRAGMA mmap_size=30000000"
                )  # Memory map for faster access
            else:
                # Read-only optimizations
                conn.execute("PRAGMA query_only=ON")  # Mark connection as read-only
                conn.execute("PRAGMA mmap_size=30000000")  # Memory map for faster reads

            yield conn
            break  # Connection successful, break the retry loop

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < 2:
                print(
                    f"[yellow]⚠️ Database locked, retrying connection in {(attempt+1)*0.5}s[/yellow]"
                )
                time.sleep((attempt + 1) * 0.5)  # Increasing delay between attempts
            else:
                raise  # Re-raise on last attempt or different error
    else:
        # This runs if the for loop completes without a break (all retries failed)
        raise sqlite3.OperationalError(
            f"Unable to connect to database {db_path} after multiple attempts"
        )

    # Clean up the connection properly
    try:
        conn.close()
    except:
        pass


def with_db_retry(max_retries=5, initial_delay=1.0, backoff_factor=2.0):
    """
    Decorator for retrying database operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay increase between retries

    Returns:
        Decorated function with retry logic
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for retry in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        print(
                            f"[yellow]⚠️ Database locked, retrying in {delay:.1f}s (attempt {retry+1}/{max_retries})[/yellow]"
                        )
                        last_exception = e
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise

            # If we've exhausted all retries
            print(f"[red]❌ Failed after {max_retries} retries[/red]")
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for retry in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        print(
                            f"[yellow]⚠️ Database locked, retrying in {delay:.1f}s (attempt {retry+1}/{max_retries})[/yellow]"
                        )
                        last_exception = e
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise

            # If we've exhausted all retries
            print(f"[red]❌ Failed after {max_retries} retries[/red]")
            raise last_exception

        # Return the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
