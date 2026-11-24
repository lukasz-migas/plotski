# Installation

The base install includes Bokeh, the default backend.

```sh
uv pip install plotski
```

Install the Plotly extra to render Plotly reports.

```sh
uv pip install 'plotski[plotly]'
```

The same package names work with `pip install`. Plotski supports Python 3.10+,
NumPy 2+, Bokeh 3.1+, and Plotly 6+.

## Static image export

Install the export extra for the backend you use.

```sh
uv pip install 'plotski[bokeh-export]'
uv pip install 'plotski[plotly-export]'
```

Bokeh uses Selenium with Chrome or Firefox and its matching driver. Put
`chromedriver` or `geckodriver` on your PATH. Plotly uses Kaleido with Chrome
or Chromium. Install the browser separately.

To run the optional browser and image export tests from a checkout, install
both export extras and the test extra, and run the following with Chrome and
ChromeDriver available.

```sh
PLOTSKI_BROWSER_TESTS=1 uv run --extra test --extra bokeh-export --extra plotly-export pytest tests/test_report_browser.py
```
