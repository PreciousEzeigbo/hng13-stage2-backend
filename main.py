from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
import httpx
import os
from dotenv import load_dotenv
import random
from PIL import Image, ImageDraw, ImageFont
import asyncio

load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model
class Country(Base):
    __tablename__ = "countries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    capital = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True, index=True)
    population = Column(Integer, nullable=False)
    currency_code = Column(String(10), nullable=True, index=True)
    exchange_rate = Column(Float, nullable=True)
    estimated_gdp = Column(Float, nullable=True)
    flag_url = Column(Text, nullable=True)
    last_refreshed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class CountryResponse(BaseModel):
    id: int
    name: str
    capital: Optional[str]
    region: Optional[str]
    population: int
    currency_code: Optional[str]
    exchange_rate: Optional[float]
    estimated_gdp: Optional[float]
    flag_url: Optional[str]
    last_refreshed_at: datetime
    
    class Config:
        from_attributes = True

class StatusResponse(BaseModel):
    total_countries: int
    last_refreshed_at: Optional[datetime]

class ErrorResponse(BaseModel):
    error: str
    details: Optional[dict] = None

app = FastAPI(title="Country Currency & Exchange API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# External API URLs
COUNTRIES_API = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
EXCHANGE_API = "https://open.er-api.com/v6/latest/USD"
IMAGE_PATH = "cache/summary.png"

os.makedirs("cache", exist_ok=True)

async def fetch_countries():
    """Fetch countries from external API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(COUNTRIES_API)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail={
            "error": "External data source unavailable",
            "details": f"Could not fetch data from RestCountries API ({COUNTRIES_API})"
            }
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from RestCountries API ({COUNTRIES_API})"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from RestCountries API ({COUNTRIES_API})"
            }
        )

async def fetch_exchange_rates():
    """Fetch exchange rates from external API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(EXCHANGE_API)
            response.raise_for_status()
            data = response.json()
            return data.get("rates", {})
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from Exchange Rate API ({EXCHANGE_API})"
            }
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from Exchange Rate API ({EXCHANGE_API})"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from Exchange Rate API ({EXCHANGE_API})"
            }
        )

def calculate_gdp(population: int, exchange_rate: Optional[float]) -> Optional[float]:
    """Calculate estimated GDP"""
    if exchange_rate is None or exchange_rate == 0:
        return None
    random_multiplier = random.uniform(1000, 2000)
    return (population * random_multiplier) / exchange_rate

def generate_summary_image(db: Session):
    """Generate summary image with top 5 countries by GDP"""
    try:
        # Get top 5 countries by GDP
        top_countries = db.query(Country).filter(
            Country.estimated_gdp.isnot(None)
        ).order_by(Country.estimated_gdp.desc()).limit(5).all()
        
        total_countries = db.query(Country).count()
        last_refresh = db.query(Country.last_refreshed_at).order_by(
            Country.last_refreshed_at.desc()
        ).first()
        
        # Create image
        img_width = 800
        img_height = 600
        img = Image.new('RGB', (img_width, img_height), color='white')
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Draw title
        draw.text((50, 30), "Country Summary Report", fill='black', font=title_font)
        
        # Draw total countries
        draw.text((50, 100), f"Total Countries: {total_countries}", fill='black', font=header_font)
        
        # Draw last refresh time
        if last_refresh:
            refresh_time = last_refresh[0].strftime("%Y-%m-%d %H:%M:%S UTC")
            draw.text((50, 140), f"Last Refreshed: {refresh_time}", fill='black', font=text_font)
        
        # Draw top 5 countries
        draw.text((50, 200), "Top 5 Countries by Estimated GDP:", fill='black', font=header_font)
        
        y_position = 240
        for idx, country in enumerate(top_countries, 1):
            gdp_formatted = f"${country.estimated_gdp:,.2f}" if country.estimated_gdp else "N/A"
            text = f"{idx}. {country.name} - {gdp_formatted}"
            draw.text((70, y_position), text, fill='black', font=text_font)
            y_position += 40
        
        # Save image
        img.save(IMAGE_PATH)
        
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        # Don't fail the entire refresh if image generation fails

@app.post("/countries/refresh", status_code=200)
async def refresh_countries():
    """Fetch and cache all countries and exchange rates"""
    db = next(get_db())
    
    try:
        # Fetch data from external APIs
        countries_data = await fetch_countries()
        exchange_rates = await fetch_exchange_rates()
        
        # Process and store countries
        refresh_time = datetime.utcnow()
        
        for country_data in countries_data:
            validation_errors = {}

            name = country_data.get("name")
            if not name:
                validation_errors["name"] = "is required"
            
            capital = country_data.get("capital")
            region = country_data.get("region")
            
            population = country_data.get("population")
            if population is None:
                validation_errors["population"] = "is required"
            elif not isinstance(population, int):
                validation_errors["population"] = "must be an integer"
            elif population < 0:
                validation_errors["population"] = "must be a non-negative integer"
            
            flag_url = country_data.get("flag")
            
            currencies = country_data.get("currencies", [])
            currency_code = None
            if currencies and isinstance(currencies, list) and len(currencies) > 0:
                currency_code = currencies[0].get("code")
            
            if validation_errors:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Validation failed", "details": validation_errors}
                )

            # Currency handling logic
            exchange_rate = None
            estimated_gdp = None
            
            if not currency_code: # This covers both empty currencies array and missing code
                currency_code = None
                exchange_rate = None
                estimated_gdp = 0
            else:
                exchange_rate = exchange_rates.get(currency_code)
                if exchange_rate is not None:
                    if population is not None:
                        estimated_gdp = calculate_gdp(population, exchange_rate)
                else:
                    exchange_rate = None
                    estimated_gdp = None
            
            # Check if country exists (case-insensitive)
            existing_country = db.query(Country).filter(
                Country.name.ilike(name)
            ).first()
            
            if existing_country:
                # Update existing country
                existing_country.capital = capital
                existing_country.region = region
                existing_country.population = population
                existing_country.currency_code = currency_code
                existing_country.exchange_rate = exchange_rate
                existing_country.estimated_gdp = estimated_gdp
                existing_country.flag_url = flag_url
                existing_country.last_refreshed_at = refresh_time
            else:
                # Insert new country
                new_country = Country(
                    name=name,
                    capital=capital,
                    region=region,
                    population=population,
                    currency_code=currency_code,
                    exchange_rate=exchange_rate,
                    estimated_gdp=estimated_gdp,
                    flag_url=flag_url,
                    last_refreshed_at=refresh_time
                )
                db.add(new_country)
        
        db.commit()
        
        # summary image
        generate_summary_image(db)
        
        total = db.query(Country).count()
        return {
            "message": "Countries refreshed successfully",
            "total_countries": total,
            "last_refreshed_at": refresh_time
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (503 from external API failures)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "details": str(e)}
        )
    finally:
        db.close()

@app.get("/countries", response_model=List[CountryResponse])
async def get_countries(
    region: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    sort: Optional[str] = Query(None)
):
    """Get all countries with optional filters and sorting"""
    db = next(get_db())
    
    try:
        query = db.query(Country)
        
        # Apply filters
        if region:
            query = query.filter(Country.region.ilike(region))
        
        if currency:
            query = query.filter(Country.currency_code.ilike(currency))
        
        # Apply sorting
        if sort == "gdp_desc":
            query = query.order_by(Country.estimated_gdp.desc())
        elif sort == "gdp_asc":
            query = query.order_by(Country.estimated_gdp.asc())
        elif sort == "population_desc":
            query = query.order_by(Country.population.desc())
        elif sort == "population_asc":
            query = query.order_by(Country.population.asc())
        else:
            query = query.order_by(Country.name)
        
        countries = query.all()
        return countries
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error"}
        )
    finally:
        db.close()

@app.get("/countries/image")
async def get_summary_image():
    """Serve the generated summary image"""
    if not os.path.exists(IMAGE_PATH):
        raise HTTPException(
            status_code=404,
            detail={"error": "Summary image not found"}
        )
    
    return FileResponse(IMAGE_PATH, media_type="image/png")

@app.get("/countries/{name}", response_model=CountryResponse)
async def get_country(name: str):
    """Get a single country by name"""
    db = next(get_db())
    
    try:
        country = db.query(Country).filter(Country.name.ilike(name)).first()
        
        if not country:
            raise HTTPException(
                status_code=404,
                detail={"error": "Country not found"}
            )
        
        return country
        
    finally:
        db.close()

@app.delete("/countries/{name}", status_code=200)
async def delete_country(name: str):
    """Delete a country by name"""
    db = next(get_db())
    
    try:
        country = db.query(Country).filter(Country.name.ilike(name)).first()
        
        if not country:
            raise HTTPException(
                status_code=404,
                detail={"error": "Country not found"}
            )
        
        db.delete(country)
        db.commit()
        
        return {"message": f"Country '{name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error"}
        )
    finally:
        db.close()

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get API status with total countries and last refresh timestamp"""
    db = next(get_db())
    
    try:
        total_countries = db.query(Country).count()
        
        # Get most recent refresh time
        last_refresh = db.query(Country.last_refreshed_at).order_by(
            Country.last_refreshed_at.desc()
        ).first()
        
        return {
            "total_countries": total_countries,
            "last_refreshed_at": last_refresh[0] if last_refresh else None
        }
        
    finally:
        db.close()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return empty 204 for favicon requests to avoid noisy 404 logs in dev."""
    return Response(status_code=204)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Country Currency & Exchange API",
        "endpoints": {
            "POST /countries/refresh": "Refresh country data from external APIs",
            "GET /countries": "Get all countries (supports ?region=, ?currency=, ?sort=)",
            "GET /countries/{name}": "Get a single country by name",
            "DELETE /countries/{name}": "Delete a country",
            "GET /status": "Get API status",
            "GET /countries/image": "Get summary image"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)