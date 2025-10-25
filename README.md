# Country Currency & Exchange API

A RESTful API that provides comprehensive country information including population, currency codes, real-time exchange rates, and estimated GDP calculations. Built with FastAPI and MySQL.

## Features

- 🌍 Fetch and cache data for 250+ countries
- 💱 Real-time currency exchange rates
- 📊 Automated GDP estimation based on population and exchange rates
- 🖼️ Auto-generated summary visualization with top 5 countries by GDP
- 🔍 Advanced filtering and sorting capabilities
- 📝 Comprehensive validation and error handling

## Tech Stack

- **Framework:** FastAPI
- **Database:** MySQL (with SQLAlchemy ORM)
- **External APIs:**
  - [RestCountries API](https://restcountries.com) - Country data
  - [Exchange Rate API](https://open.er-api.com) - Currency exchange rates
- **Image Processing:** Pillow (PIL)
- **HTTP Client:** HTTPX (async)

## Installation

### Prerequisites

- Python 3.10+
- MySQL 8.0+
- pip and virtualenv

### Local Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/PreciousEzeigbo/hng13-stage2-backend.git
   cd hng13-stage2-backend
   ```

2. **Create and activate virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up MySQL database:**

   ```bash
   mysql -u root -p
   ```

   ```sql
   CREATE DATABASE country_currency_db;
   CREATE USER 'countryapp'@'localhost' IDENTIFIED BY 'YourPassword';
   GRANT ALL PRIVILEGES ON country_currency_db.* TO 'countryapp'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

5. **Configure environment variables:**

   Create a `.env` file in the project root:

   ```env
   DATABASE_URL=mysql+pymysql://countryapp:YourPassword@localhost:3306/country_currency_db
   PORT=8000
   ```

   **Note:** If your password contains special characters, URL-encode them:

   - `@` → `%40`
   - `:` → `%3A`
   - `/` → `%2F`

6. **Run the application:**

   ```bash
   uvicorn main:app --reload
   ```

7. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## API Endpoints

### Country Management

#### `POST /countries/refresh`

Fetch and cache all countries from external APIs with exchange rates and GDP calculations.

**Response:**

```json
{
  "message": "Countries refreshed successfully",
  "total_countries": 250,
  "last_refreshed_at": "2025-10-25T12:00:00"
}
```

#### `GET /countries`

Get all countries with optional filtering and sorting.

**Query Parameters:**

- `region` - Filter by region (e.g., `Africa`, `Europe`)
- `currency` - Filter by currency code (e.g., `USD`, `EUR`)
- `sort` - Sort results:
  - `gdp_desc` - By GDP (highest first)
  - `gdp_asc` - By GDP (lowest first)
  - `population_desc` - By population (highest first)
  - `population_asc` - By population (lowest first)

**Example:**

```bash
curl "http://localhost:8000/countries?region=Africa&sort=gdp_desc"
```

**Response:**

```json
[
  {
    "id": 1,
    "name": "Nigeria",
    "capital": "Abuja",
    "region": "Africa",
    "population": 206139589,
    "currency_code": "NGN",
    "exchange_rate": 411.0,
    "estimated_gdp": 753892847.15,
    "flag_url": "https://flagcdn.com/ng.svg",
    "last_refreshed_at": "2025-10-25T12:00:00"
  }
]
```

#### `GET /countries/{name}`

Get a single country by name (case-insensitive).

**Example:**

```bash
curl "http://localhost:8000/countries/Nigeria"
```

#### `DELETE /countries/{name}`

Delete a country by name.

**Example:**

```bash
curl -X DELETE "http://localhost:8000/countries/Nigeria"
```

### Status & Visualization

#### `GET /status`

Get API status with total countries and last refresh timestamp.

**Response:**

```json
{
  "total_countries": 250,
  "last_refreshed_at": "2025-10-25T12:00:00"
}
```

#### `GET /countries/image`

Download auto-generated summary image showing:

- Total countries in database
- Last refresh timestamp
- Top 5 countries by estimated GDP

**Response:** PNG image file

## Data Models

### Country Schema

```json
{
  "id": 1,
  "name": "string",
  "capital": "string | null",
  "region": "string | null",
  "population": 0,
  "currency_code": "string | null",
  "exchange_rate": 0.0,
  "estimated_gdp": 0.0,
  "flag_url": "string | null",
  "last_refreshed_at": "datetime"
}
```

## Currency Handling Logic

1. **Multiple currencies:** Only the first currency code is stored
2. **Empty currencies array:**
   - `currency_code` = `null`
   - `exchange_rate` = `null`
   - `estimated_gdp` = `0`
3. **Currency not in exchange API:**
   - `exchange_rate` = `null`
   - `estimated_gdp` = `null`

## Deployment (AWS EC2 + Nginx)

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3-pip python3-venv mysql-server nginx -y

# Clone repository
git clone https://github.com/PreciousEzeigbo/hng13-stage2-backend.git
cd hng13-stage2-backend

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. MySQL Configuration

```bash
sudo mysql_secure_installation
sudo mysql
```

```sql
CREATE DATABASE country_currency_db;
CREATE USER 'countryapp'@'localhost' IDENTIFIED BY 'StrongPassword';
GRANT ALL PRIVILEGES ON country_currency_db.* TO 'countryapp'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Environment Variables

Create `.env` file:

```env
DATABASE_URL=mysql+pymysql://countryapp:StrongPassword@localhost:3306/country_currency_db
PORT=8000
```

### 4. Systemd Service

Create `/etc/systemd/system/country-api.service`:

```ini
[Unit]
Description=Country Currency API
After=network.target mysql.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/hng13-stage2-backend
Environment="PATH=/home/ubuntu/hng13-stage2-backend/venv/bin"
ExecStart=/home/ubuntu/hng13-stage2-backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable country-api
sudo systemctl start country-api
```

### 5. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/country-api`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or EC2 public IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/country-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Security Group (AWS)

Allow inbound traffic:

- **Port 80** (HTTP)
- **Port 443** (HTTPS - optional with SSL)
- **Port 22** (SSH)

Block:

- Port 3306 (MySQL - only accessible locally)
- Port 8000 (FastAPI - only accessible via Nginx)

## Error Handling

The API provides detailed error responses:

```json
{
  "detail": {
    "error": "Error type",
    "details": "Specific error information"
  }
}
```

**Common HTTP Status Codes:**

- `200` - Success
- `400` - Validation failed
- `404` - Resource not found
- `500` - Internal server error
- `503` - External API unavailable

## Validation Rules

- **Name:** Required, unique (case-insensitive)
- **Population:** Required, must be integer >= 0 (allows 0 for uninhabited territories)
- **Currency Code:** Optional (3-letter code)
- **Capital:** Optional
- **Region:** Optional

## Development

### Run tests:

```bash
# Coming soon
pytest
```

### Format code:

```bash
black main.py
```

### Lint:

```bash
flake8 main.py
```

## Project Structure

```
hng13-stage2-backend/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── .gitignore          # Git ignore rules
├── cache/              # Generated images (auto-created)
│   └── summary.png
└── README.md           # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is part of the HNG Internship Stage 2 Backend challenge.

## Author

**Precious Ezeigbo**

- GitHub: [@PreciousEzeigbo](https://github.com/PreciousEzeigbo)

## Acknowledgments

- [RestCountries API](https://restcountries.com) for country data
- [Exchange Rate API](https://open.er-api.com) for currency exchange rates
- [FastAPI](https://fastapi.tiangolo.com) for the amazing framework

## Support

For issues or questions, please open an issue on GitHub.

---

**Built with ❤️ for HNG Internship 13**
