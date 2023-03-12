# geodata

Geographically-relevant data files to assist scrapers

## demonyms.csv

Can be used to map nationality to country.

CSV format:

nationality,country

sourced from:
https://github.com/knowitall/chunkedextractor/blob/master/src/main/resources/edu/knowitall/chunkedextractor/demonyms.csv

### example usage

This is loaded in the `py_common/base_python_scraper.py` during class initialisation, and then made available in the class member function, `_get_country_for_nationality`

You can call it like this in a derived class:

```python
nationality = 'French'
country = self._get_country_for_nationality(nationality)
print(country)  # France
```

See `scrapers/life_selector.py` for actual usage of this.
