from django import template

register = template.Library()


@register.simple_tag
def mapaction_left_menu():
    """Replaces GeoNode's left menu (All resources, Datasets, Maps, Documents, GeoStories, Dashboards)."""
    return [
        {"type": "link", "href": "/mapaction/emergencies/", "label": "Emergencies"},
        {"type": "link", "href": "/catalogue/#/search/?f=document", "label": "All maps"},
        {"type": "link", "href": "https://mapaction.org", "label": "MapAction.org", "target": "_blank"},
    ]


@register.simple_tag
def mapaction_current_emergencies():
    """The emergencies MapAction staff marked as current (admin > Emergencies), for the red bar."""
    from mapaction.models import Emergency

    return [{"label": e.short_label or e.title, "url": e.get_absolute_url()}
            for e in Emergency.objects.filter(is_current=True).order_by("-code")[:4]]
