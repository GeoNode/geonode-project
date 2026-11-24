from geonode.facets.providers.region import RegionFacetProvider


class CountryFacetProvider(RegionFacetProvider):
    """GeoNode's Region filter, labelled the way MapAction talks about it."""

    def get_info(self, lang="en", **kwargs):
        info = super().get_info(lang=lang, **kwargs)
        info["label"] = "Country"
        return info

    @classmethod
    def register(cls, registry, **kwargs) -> None:
        # GeoNode's RegionFacetProvider.register() instantiates its own class; register ours instead
        registry.register_facet_provider(cls(**kwargs))
