import csv

from app.db.database import session_scope, Base, engine
from app.db.models import Book

Base.metadata.create_all(bind=engine)

with open('book_catalog_sample.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    with session_scope() as session:
        for row in reader:
            book = Book(
                title=row['title'],
                author=row['author'],
                price=float(row['price']),
                genre=row['genre'],
                cover_url=row['cover_url'] or None,
                description=row['description'] or None,
                rating=float(row['rating']) if row['rating'] else None,
                year=int(row['year']) if row['year'] else None,
                in_top=False
            )
            session.add(book)

print('success')