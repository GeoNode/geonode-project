ARG BASE_IMAGE_VERSION
FROM geonode/nginx:${BASE_IMAGE_VERSION}

# Exposes perf_tool at /performance — see performance.conf for why this has
# to be baked into the image (not bind-mounted) and why the location block
# needs its specific ^~ / literal-proxy_pass shape.
COPY performance.conf /etc/nginx/sites-enabled/performance.conf
