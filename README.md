# plotski

[![PyPI](https://img.shields.io/pypi/v/plotski.svg)](https://pypi.python.org/pypi/plotski)
[![Docs](https://readthedocs.org/projects/plotski/badge/?version=latest)](https://plotski.readthedocs.io/en/latest/?version=latest)
[![Updates](https://pyup.io/repos/github/lukasz-migas/plotski/shield.svg)](https://pyup.io/repos/github/lukasz-migas/plotski/)
[![tests](https://github.com/lukasz-migas/plotski/actions/workflows/test_and_deploy.yml/badge.svg)](https://github.com/lukasz-migas/plotski/actions/workflows/test_and_deploy.yml)

Package to generate easily generate interactive figures and export them to HTML documents.

The idea behind this package is to provide an easy-to-use interface to generate structured 
HTML documents with interactive visualisations. The library is not meant to fill every gap
but to provide several common plot types such as `line`, `scatter` or `image` type-plots and
additional annotations and enable easy exportation to HTML document.

All plots are generated using the excellent `bokeh` library.

Typical usage might be

```python
import numpy as np
from plotski import PlotStore

x = np.arange(100)
y = np.random.randint(0, 500, 100)

store = PlotStore(
    ".",  # this will save the plot to current working directory.
)
tab_name = store.add_tab("Random plot")
# data is provided in dictionary. Data validation happens during plot generation
store.plot_spectrum(tab_name, {"x": x, "y": y})
# this will generate the HTML document (in memory using temporary file)
store.show()
# you can instead save to disk which will save the document to disk
store.save()
```

## Features


## Planned

* Improve generation of layouts.
* Improve modification of plot parameters.
* Add custom JS support.


## Licence
Free software: MIT license

## Documentation
https://plotski.readthedocs.io