# Dev Container

A development setup for working on GeoNode inside Docker, with VS Code debugging ready to go.

## 1. Start the containers

```bash
cd ./.devcontainer
./docker.sh build
./docker.sh up -d
```

`docker.sh` is a thin wrapper that loads `../.env` and runs `docker compose` with both the base `docker-compose.yml` and this folder's override.

Then, in VS Code, open the Command Palette (`Ctrl+Shift+P`, or `Ctrl+P` and type `>`) and run **Dev Containers: Reopen in Container** to attach the editor to the running container.

## 2. Services start idle

The `django` and `celery` containers start **without** their services running (their command is `sleep infinity` in `docker-compose.yml`). This lets you exec into a container and start the services yourself, so you stay in control of when and how they run.

## 3. Debugging from VS Code

The container ships preconfigured with the Python extension and VS Code settings (`.vscode/launch.json`) ready to launch **Django** and **Celery** debug sessions.

- The containers run **synchronously** (`ASYNC_SIGNALS` is `False`).
- You can also start Django the plain way instead of the debugger:

  ```bash
  django-admin runserver 0.0.0.0:8000
  ```

## 4. Editable GeoNode / mapstore-client

`geonode` and `geonode-mapstore-client` are installed in the venv like a standard GeoNode deployment.

To work on them in **editable** mode, the `.devrequirements/` folder (mounted at `/usr/src/.devrequirements`) contains `install-editable-requirements.sh` (take care of making it executable with `chmod +x`), which installs both packages as editable git checkouts into that folder.

The `docker-compose.yml` override also prepends `PYTHONPATH` with those paths. Because the editable packages live in the mounted folder, the installation is **retained across container restarts and rebuilds**.
