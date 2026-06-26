# TaxLabelTR Neon + Render + Hugging Face Setup

Bu proje icin onerilen cloud veritabani Neon PostgreSQL'dir.

## Neden Neon?

- Kod FastAPI + SQLAlchemy + Alembic ile standart PostgreSQL kullaniyor.
- Neon tek `DATABASE_URL` ile dogrudan baglaniyor.
- `sslmode=require` destekli standart Postgres connection string veriyor.
- Branching ve instant restore ozellikleri etiketleme verisini korumak icin pratik.
- Supabase de olur, fakat bu projede Supabase Auth, Storage veya Data API kullanilmiyor.

## 1. Neon'da database olustur

1. https://console.neon.tech adresinde proje olustur.
2. Region olarak mumkunse backend'in calisacagi yere yakin bir bolge sec.
3. Dashboard'da `Connect` butonuna bas.
4. Connection string'i kopyala.

Ornek:

```text
postgresql://neondb_owner:password@ep-example.us-east-2.aws.neon.tech/neondb?sslmode=require
```

## 2. Lokalde `.env` olustur

```powershell
cd "C:\Users\zeyne\OneDrive\Documentos\Masaüstü\TaxLabelTR\backend"
.\scripts\setup_neon.ps1
```

Script Neon `DATABASE_URL`, admin email ve admin sifreni sorar. `backend/.env` dosyasini otomatik olusturur.

## 3. Tablolari Neon'a kur

```powershell
cd "C:\Users\zeyne\OneDrive\Documentos\Masaüstü\TaxLabelTR\backend"
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\alembic.exe upgrade head
& .\.venv\Scripts\python.exe scripts\db_status.py
```

## 4. Render backend env ayarlari

Render Web Service icin:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: bash start.sh
```

Environment Variables:

```text
DATABASE_URL=Neon connection string
SECRET_KEY=long-random-secret
ADMIN_USERNAME=admin
ADMIN_EMAIL=your-email@example.com
ADMIN_PASSWORD=strong-password
ACCESS_TOKEN_EXPIRE_MINUTES=1440
QUIZ_PASSING_SCORE=80
CORS_ORIGINS=https://your-huggingface-space.hf.space
```

## 5. Hugging Face frontend ayari

Hugging Face Space Settings > Variables:

```text
VITE_API_BASE_URL=https://your-render-service.onrender.com/api
```

Sonra frontend build:

```powershell
cd "C:\Users\zeyne\OneDrive\Documentos\Masaüstü\TaxLabelTR\frontend"
npm run build
```

`frontend/dist` icerigini Hugging Face Static Space'e yukle.

## 6. Backup

Admin panel/API backup:

```text
GET /api/admin/backup
```

Terminalden tam dump:

```powershell
cd "C:\Users\zeyne\OneDrive\Documentos\Masaüstü\TaxLabelTR\backend"
.\scripts\backup_neon.ps1
```
