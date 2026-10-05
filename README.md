# Colorado Producers Data Set

A compiled data set of Colorado farms, ranches, markets and food businesses that sell
to the public, with a summary, map and table: https://dbrown-creator.github.io/colorado-producers-data/

**Sources:**
- Colorado Proud Farm Fresh Directory and member directory (Colorado Department of Agriculture)
- Colorado Farmers Market Association
- USDA local food directories
- Chaffee Provides
- Farmers market vendor lists

Listings are checked against each producer's own website where one exists.

- `data/producers.csv`: the full data set
- `data/producers.json` and `data/summary.json`: what the page reads
- `scripts/build_data.py`: rebuilds them from the compiled data set:
  `python scripts/build_data.py --inputs ../colorado-farm-trail`
