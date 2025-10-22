"""
Enrichment module for issue data enhancement.
"""

from .component_taxonomy import ComponentTaxonomy
from .attribute_extractor import AttributeExtractor
from .metadata_enricher import MetadataEnricher

__all__ = ['ComponentTaxonomy', 'AttributeExtractor', 'MetadataEnricher']

