import asyncio
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

@dataclass
class Book:
    """Represents a single library book."""
    book_id:  str
    title:    str
    author:   str
    category: str
    copies:   int = 1

@dataclass
class BorrowRecord:
    """Tracks an active loan."""
    record_id:   str
    user_id:     str
    book_id:     str
    borrow_date: date
    due_date:    date
    returned:    bool = False

    @property
    def is_overdue(self) -> bool:
        return not self.returned and date.today() > self.due_date

    @property
    def fine(self) -> float:
        """Le 5,000 per overdue day."""
        if not self.is_overdue:
            return 0.0
        days_late = (date.today() - self.due_date).days
        return days_late * 5_000.0


BOOKS_DB: Dict[str, Book] = {
    "B001": Book("B001", "Python Crash Course",       "Eric Matthes",     "Programming", copies=3),
    "B002": Book("B002", "Clean Code",                "Robert C. Martin", "Programming", copies=2),
    "B003": Book("B003", "Introduction to Algorithms","Cormen et al.",    "Computer Science", copies=1),
    "B004": Book("B004", "The Great Gatsby",          "F. Scott Fitzgerald","Fiction",   copies=4),
    "B005": Book("B005", "Digital Marketing",         "Ryan Deiss",       "Business",   copies=2),
}

BORROW_DB: Dict[str, BorrowRecord] = {
    # Pre-seeded overdue record for demonstration
    "R000": BorrowRecord(
        record_id="R000",
        user_id="U99",
        book_id="B003",
        borrow_date=date.today() - timedelta(days=20),
        due_date=date.today() - timedelta(days=6),   # 6 days overdue
    )
}

_record_counter: int = 1   # auto-increment for record IDs


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────
# Endpoint 1: GET /books/search
# Purpose : Search for books by title, author, or category
# Input   : query (str), field ("title" | "author" | "category")
# Output  : List of matching Book dicts, or empty list
# ─────────────────────────────────────────────

async def get_books_search(query: str, search_field: str = "title") -> dict:
    """
    Simulate GET /books/search?query=...&field=...
    Performs a case-insensitive substring match.
    """
    await asyncio.sleep(0.1)   # simulate DB query latency

    query_lower = query.lower()
    results: List[dict] = []

    for book in BOOKS_DB.values():
        target = getattr(book, search_field, "").lower()
        if query_lower in target:
            results.append({
                "book_id":  book.book_id,
                "title":    book.title,
                "author":   book.author,
                "category": book.category,
                "copies_available": book.copies,
            })

    return {
        "endpoint": "GET /books/search",
        "query":    query,
        "field":    search_field,
        "results":  results,
        "count":    len(results),
    }


# ─────────────────────────────────────────────
# Endpoint 2: POST /books/borrow
# Purpose : Allow a user to borrow a book (14-day loan period)
# Input   : user_id (str), book_id (str)
# Output  : New BorrowRecord dict, or error message
# ─────────────────────────────────────────────

async def post_borrow_book(user_id: str, book_id: str) -> dict:
    """
    Simulate POST /books/borrow  { user_id, book_id }
    Checks availability and creates a borrow record.
    """
    global _record_counter
    await asyncio.sleep(0.15)  # simulate write latency

    if book_id not in BOOKS_DB:
        return {"endpoint": "POST /books/borrow", "success": False,
                "error": f"Book '{book_id}' not found."}

    book = BOOKS_DB[book_id]
    if book.copies < 1:
        return {"endpoint": "POST /books/borrow", "success": False,
                "error": f"No copies of '{book.title}' are currently available."}

    # Check user doesn't already have this book
    for rec in BORROW_DB.values():
        if rec.user_id == user_id and rec.book_id == book_id and not rec.returned:
            return {"endpoint": "POST /books/borrow", "success": False,
                    "error": f"User '{user_id}' already has '{book.title}' on loan."}

    # Create the record
    record_id = f"R{_record_counter:03d}"
    _record_counter += 1
    today = date.today()
    record = BorrowRecord(
        record_id=record_id,
        user_id=user_id,
        book_id=book_id,
        borrow_date=today,
        due_date=today + timedelta(days=14),
    )
    BORROW_DB[record_id] = record
    book.copies -= 1

    return {
        "endpoint":    "POST /books/borrow",
        "success":     True,
        "record_id":   record_id,
        "user_id":     user_id,
        "book_title":  book.title,
        "borrow_date": str(record.borrow_date),
        "due_date":    str(record.due_date),
    }


# ─────────────────────────────────────────────
# Endpoint 3: POST /books/return
# Purpose : Mark a borrowed book as returned; calculate any fine
# Input   : record_id (str)
# Output  : Return confirmation with fine amount (if any)
# ─────────────────────────────────────────────

async def post_return_book(record_id: str) -> dict:
    """
    Simulate POST /books/return  { record_id }
    Marks the loan as returned and restores the copy count.
    """
    await asyncio.sleep(0.15)

    if record_id not in BORROW_DB:
        return {"endpoint": "POST /books/return", "success": False,
                "error": f"Record '{record_id}' not found."}

    record = BORROW_DB[record_id]
    if record.returned:
        return {"endpoint": "POST /books/return", "success": False,
                "error": f"Record '{record_id}' is already marked as returned."}

    fine = record.fine          # capture before marking returned
    record.returned = True
    BOOKS_DB[record.book_id].copies += 1

    return {
        "endpoint":  "POST /books/return",
        "success":   True,
        "record_id": record_id,
        "user_id":   record.user_id,
        "book_title": BOOKS_DB[record.book_id].title,
        "returned_date": str(date.today()),
        "fine_leones": fine,
        "message": (f"Fine of Le {fine:,.0f} is due." if fine > 0
                    else "Returned on time. No fine."),
    }


# ─────────────────────────────────────────────
# Endpoint 4: GET /books/overdue
# Purpose : List all overdue loans with fine amounts
# Input   : (none – admin endpoint)
# Output  : List of overdue BorrowRecord dicts
# ─────────────────────────────────────────────

async def get_overdue_books() -> dict:
    """
    Simulate GET /books/overdue
    Returns every active loan past its due date.
    """
    await asyncio.sleep(0.1)

    overdue: List[dict] = []
    for rec in BORROW_DB.values():
        if rec.is_overdue:
            book_title = BOOKS_DB.get(rec.book_id, Book("?", "Unknown", "", "")).title
            overdue.append({
                "record_id":  rec.record_id,
                "user_id":    rec.user_id,
                "book_title": book_title,
                "due_date":   str(rec.due_date),
                "days_late":  (date.today() - rec.due_date).days,
                "fine_leones": rec.fine,
            })

    return {
        "endpoint": "GET /books/overdue",
        "overdue_count": len(overdue),
        "records": overdue,
    }


# ══════════════════════════════════════════════════════════════════
#  PART B  –  IMPLEMENTATION
#  Async simulation of multiple users accessing the system
#  simultaneously (borrow & return flows)
# ══════════════════════════════════════════════════════════════════

def _banner(text: str) -> None:
    print(f"\n{'═' * 62}")
    print(f"  {text}")
    print(f"{'═' * 62}")

def _section(text: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {text}")
    print(f"{'─' * 62}")

def _pretty(response: dict) -> None:
    """Print key response fields in a readable way."""
    ep = response.pop("endpoint", "")
    print(f"   {ep}")
    for k, v in response.items():
        if k == "results" and isinstance(v, list):
            for item in v:
                print(f"      • {item}")
        elif k == "records" and isinstance(v, list):
            for item in v:
                print(f"      • {item}")
        else:
            print(f"     {k}: {v}")


async def simulate_user_session(
    user_id: str,
    book_id: str,
    search_query: str,
    search_field: str = "title",
) -> None:
    """
    Simulates one user's full session:
      1. Search for a book
      2. Borrow it
      3. (Optionally) return it immediately
    """
    print(f"\n [{user_id}] Session started")

    # Step 1 – Search
    search_resp = await get_books_search(search_query, search_field)
    print(f"   [{user_id}] Search '{search_query}' → {search_resp['count']} result(s)")

    # Step 2 – Borrow
    borrow_resp = await post_borrow_book(user_id, book_id)
    print(f"   [{user_id}] Borrow '{book_id}' → success={borrow_resp['success']}", end="")
    if borrow_resp["success"]:
        print(f"  | record={borrow_resp['record_id']} | due={borrow_resp['due_date']}")
    else:
        print(f"  |   {borrow_resp['error']}")
        return                          # nothing to return

    # Step 3 – Return (random delay to simulate real usage)
    await asyncio.sleep(random.uniform(0.1, 0.4))
    return_resp = await post_return_book(borrow_resp["record_id"])
    print(f"  [{user_id}] Return '{book_id}' → {return_resp['message']}")


async def run_demo() -> None:
    """Full demonstration of all four endpoints plus concurrent users."""

    _banner("PROG315 – LIMKOKWING LIBRARY API  |  ASYNC DEMO")

    # ── Part A: Show each endpoint in isolation ──────────────────

    _section("ENDPOINT 1 — GET /books/search")
    r = await get_books_search("python", "title")
    _pretty(r)

    r = await get_books_search("Robert", "author")
    _pretty(r)

    r = await get_books_search("Programming", "category")
    _pretty(r)

    _section("ENDPOINT 2 — POST /books/borrow")
    r = await post_borrow_book("U01", "B001")
    _pretty(r)

    r = await post_borrow_book("U02", "B002")
    _pretty(r)

    # Attempt to borrow a book with no copies
    r = await post_borrow_book("U03", "B003")   # only 1 copy, pre-borrowed by R000
    _pretty(r)

    _section("ENDPOINT 3 — POST /books/return")
    # Return the overdue pre-seeded record
    r = await post_return_book("R000")
    _pretty(r)

    # Return a record just created above
    r = await post_return_book("R001")
    _pretty(r)

    _section("ENDPOINT 4 — GET /books/overdue")
    r = await get_overdue_books()
    _pretty(r)

    # ── Part B: Concurrent multi-user simulation ─────────────────

    _section("CONCURRENT USER SIMULATION  (asyncio.gather)")
    print("  Simulating 5 users borrowing/returning books at the same time …\n")

    sessions = [
        simulate_user_session("U10", "B004", "great gatsby",  "title"),
        simulate_user_session("U11", "B005", "marketing",     "title"),
        simulate_user_session("U12", "B001", "Eric",          "author"),
        simulate_user_session("U13", "B002", "Programming",   "category"),
        simulate_user_session("U14", "B004", "Fiction",       "category"),
    ]

    await asyncio.gather(*sessions)

    _section("FINAL OVERDUE STATUS")
    r = await get_overdue_books()
    _pretty(r)

    _banner(" DEMO COMPLETE")


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    asyncio.run(run_demo())