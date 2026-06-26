## Backend (FastAPI) - İskelet

Bu klasör, FastAPI + SQLAlchemy + Alembic tabanlı backend'in **mimari iskeletini** ve **veritabanı modellerini** içerir.

Bu adımda **API endpointleri**, **frontend** ve **Docker** bilinçli olarak eklenmemiştir.

### Klasör Yapısı (özet)

- `app/`: Uygulama kodu
  - `core/`: ayarlar, güvenlik, ortak yardımcılar
  - `db/`: SQLAlchemy engine/session, base, modeller
  - `schemas/`: Pydantic şema taslakları (bu adımda sadece isim/iskele)
  - `modules/`: modül bazlı organizasyon (auth, users, documents, training, quiz, labeling, admin, export, dashboard)
- `alembic/`: migration ortamı ve sürümler
- `alembic.ini`: Alembic konfigürasyonu (DB URL runtime'da `DATABASE_URL` ile alınır)

