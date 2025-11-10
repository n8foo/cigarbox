CigarBox
========
A smokin' fast personal photostream

# design points

* Tag-based organization with multi-tag intersection filtering
* Privacy controls: public, private, friends, family
* Similar nomenclature to Flickr (photos, photosets, galleries, tags)
* SHA1-based deduplication
* Multiple thumbnail sizes
* Proof-of-work bot defense against AI scrapers
* Dual Flask apps: web UI + RESTful API
* SQLite + Peewee ORM (lightweight, fast)
* #simplify

# quick start
```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.py.example config.py
# Edit config.py with AWS credentials

# Run locally
python web.py  # Web UI on http://localhost:9600
python api.py  # API on http://localhost:9601

# Deploy
fab deploy              # Deploy to test
fab deploy --role=prod  # Deploy to production
```

# architecture
* **web.py** - User-facing web interface (port 9600)
* **api.py** - RESTful API (port 9601)
* **Images** - Served directly from S3
* **Database** - SQLite with Peewee ORM
* **Deployment** - Docker containers, Fabric automation
