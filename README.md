# Bilka2Go Scraper

A web scraper for Bilka2Go (Danish supermarket chain) that extracts product information from various categories and stores the data in Google BigQuery.

## 🚀 Features

- **Multi-category scraping**: Scrapes products from 23 different categories
- **Structured data extraction**: Extracts product details including name, price, producer, quantity, and labels
- **BigQuery integration**: Automatically stores scraped data in Google BigQuery
- **Docker support**: Containerized application for easy deployment
- **CI/CD pipeline**: Automated testing and deployment with GitHub Actions
- **Caching**: Built-in caching for improved performance
- **Robust error handling**: Comprehensive logging and error management

## 📋 Requirements

- Python 3.12+
- Google Cloud Platform account with BigQuery API enabled
- Docker (optional, for containerized deployment)

## 🛠️ Installation

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bilka2go-scraper
   ```

2. **Install UV (recommended package manager)**
   ```bash
   pip install uv
   ```

2. **Create and activate a virtual environment**
   ```bash
   uv venv
   ```
   and 
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   uv sync
   ```
    or 
   ```bash
   uv pip install -e .
   ```

5. **Install Playwright browsers**
   ```bash
   playwright install
   ```

### Docker Setup

1. **Build the Docker image**
   ```bash
   docker build -t bilka2go-scraper .
   ```

2. **Run the container**
   ```bash
   docker run -v $(pwd)/key.json:/usr/local/appuser/key.json -e GOOGLE_APPLICATION_CREDENTIALS=/usr/local/appuser/key.json bilka2go-scraper
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=your-gcp-project-id
GOOGLE_CLOUD_BIGQUERY_DATASET=your-bq-dataset-name
```

Alternatively

### Google Cloud Setup

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable BigQuery API**
   - Navigate to APIs & Services > Library
   - Search for "BigQuery API" and enable it

3. **Create Service Account**
   - Go to IAM & Admin > Service Accounts
   - Create a new service account with BigQuery Admin role
   - Download the JSON key file and save it as `key.json` in the project root

4. **Set up BigQuery Dataset**
   - The scraper will automatically create the dataset and table if they don't exist
   - Or manually create them in the BigQuery console

## 🚀 Usage

### Command Line Arguments

The scraper supports various command line arguments:

```bash
# Make sure your virtual environment is activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

python src/main.py [OPTIONS]
```

#### Available Options:

- `--category`: Specify a category to scrape (default: all)
- `--headless`: Run the browser in headless mode (default: True)
- `--verbose`: Enable verbose logging (default: False)
- `--log-level`: Set the logging level (default: INFO)

#### Examples:

```bash
# Activate virtual environment first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Scrape all categories (default)
python src/main.py

# Scrape a specific category
python src/main.py --category fruits-and-vegetables

# Run with verbose logging
python src/main.py --verbose

# Run with different log level
python src/main.py --log-level DEBUG

# Run in non-headless mode (with visible browser)
python src/main.py --headless
```

### Available Categories

The scraper supports the following categories:

| Danish Name | English Translation |
|-------------|-------------------|
| frugt-og-groent | fruits-and-vegetables |
| koed-og-fisk | meat-and-fish |
| mejeri-og-koel | dairy-and-chilled |
| drikkevarer | beverages |
| broed-og-kager | bread-and-cakes |
| kolonial | groceries |
| mad-fra-hele-verden | world-food |
| slik-og-snacks | sweets-and-snacks |
| frost | frozen-food |
| kiosk | kiosk |
| dyremad | pet-food |
| husholdning | household |
| personlig-pleje | personal-care |
| baby-og-boern | baby-and-children |
| bolig-og-koekken | home-and-kitchen |
| fritid-og-sport | leisure-and-sport |
| toej-og-sko | clothing-and-shoes |
| elektronik | electronics |
| have | garden |
| leg | toys |
| byggemarked | hardware-store |
| biludstyr | car-accessories |

## 📊 Data Structure

The scraper extracts the following information for each product:

```json
{
  "name": "Product Name",
  "price": "Price in DKK",
  "image_url": "Product image URL",
  "product_url": "Product page URL",
  "producer": "Brand/Producer",
  "quantity": "Package size/quantity",
  "price_per_unit": "Price per unit (kg, L, etc.)",
  "label1": "Product label 1",
  "label2": "Product label 2",
  "label3": "Product label 3",
  "category": "Product category",
  "scraped_at": "Timestamp"
}
```

## 🏗️ Architecture

```
src/
├── main.py              # Main scraper logic
├── config/              # Configuration files (empty)
├── models/              # Data models (empty)
├── services/            # Business logic services (empty)
├── storage/             # Scraped data storage (JSON files)
│   ├── baby-and-children/
│   ├── beverages/
│   ├── bread-and-cakes/
│   └── ...
└── utils/
    ├── __init__.py
    └── bigquery_connector.py  # BigQuery integration
```

## 🔄 CI/CD Pipeline

The project includes a GitHub Actions workflow that:

1. **Testing**: Runs tests on Python 3.12
2. **Docker Build**: Builds Docker image for pull requests
3. **Docker Push**: Pushes to Google Artifact Registry on main branch

### Required Secrets

Configure the following secrets in your GitHub repository:

- `SERVICE_ACCOUNT`: GCP service account email
- `PROJECT_ID`: Google Cloud project ID
- `SERVICE_ACCOUNT_KEY`: Service account JSON key
- `GAR_REGION`: Google Artifact Registry region
- `GAR_REPO`: Google Artifact Registry repository name

## 📝 Development

### Virtual Environment

Always activate your virtual environment before development:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

To deactivate when done:
```bash
deactivate
```

### Project Structure

- **crawl4ai**: Web scraping framework with Playwright backend
- **Google Cloud BigQuery**: Data warehouse for storing scraped data
- **loguru**: Advanced logging
- **python-dotenv**: Environment variable management

### Adding New Categories

1. Add the Danish category name to `CATEGORIES_DK` list
2. Add the translation to `CATEGORIES_TRANSLATED` dictionary
3. Update the README with the new category

### Customizing Data Extraction

Modify the `EXTRACTION_STRATEGY` in `main.py` to add or change extracted fields:

```python
EXTRACTION_STRATEGY = JsonCssExtractionStrategy(
    schema={
        "name": "product_list",
        "baseSelector": "div.product-item",
        "fields": [
            {
                "name": "new_field",
                "selector": "css-selector",
                "type": "text",  # or "attribute"
            },
            # ... existing fields
        ],
    }
)
```

## 🐛 Troubleshooting

### Common Issues

1. **Playwright Browser Not Found**
   ```bash
   # Make sure virtual environment is activated
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   playwright install
   ```

2. **BigQuery Authentication Error**
   - Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account key
   - Verify the service account has BigQuery Admin permissions

3. **Memory Issues**
   - The scraper includes built-in delays and rate limiting
   - Adjust timeouts in the crawler configuration if needed

### Logs

Logs are written to the console only. To view logs in real-time or save them to a file, you can use:

```bash
# View logs in real-time and save to file
python src/main.py | tee scraper.log

# Save logs to file only
python src/main.py > scraper.log 2>&1

# Search for errors in saved logs
grep -i error scraper.log
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support, please open an issue in the GitHub repository or contact the maintainers.

---

**Note**: This scraper is for educational and research purposes. Please respect the website's robots.txt and terms of service when using this tool.
