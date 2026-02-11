# Migration Guide: v0.2 → v0.3

This guide helps developers migrate from v0.2 to v0.3 restructured codebase.

## Overview

Version 0.3.0 introduces a major restructuring of the project for production readiness:
- **Backend**: `hie/` → `Engine/` (enterprise-grade naming)
- **Frontend**: `portal/` → `Portal/` (title case convention)
- **Service**: `hie-api` → `hie-manager` (clarifies orchestrator role)
- **Docker**: `docker-compose.full.yml` → `docker-compose.yml` (primary stack)
- **Cleanup**: Removed 16 empty placeholder directories

## Breaking Changes

### 1. Python Import Paths

**Before (v0.2):**
```python
from hie.core.message import Message
from hie.api.server import run_server
from hie.items.receivers.http_receiver import HTTPReceiver
```

**After (v0.3):**
```python
from Engine.core.message import Message
from Engine.api.server import run_server
from Engine.items.receivers.http_receiver import HTTPReceiver
```

**Migration:** Use find/replace in your IDE:
- Find: `from hie.`
- Replace: `from Engine.`

### 2. Docker Service Names

**Before (v0.2):**
- Service: `hie-api`
- Container: `hie-api`

**After (v0.3):**
- Service: `hie-manager`
- Container: `hie-manager`

**Migration:** Update docker-compose.override.yml or any scripts referencing the service.

### 3. Folder Structure

**Before (v0.2):**
```
HIE/
├── hie/          # Backend
├── portal/       # Frontend
├── core/         # Empty
├── items/        # Empty
└── ...
```

**After (v0.3):**
```
HIE/
├── Engine/       # Backend
├── Portal/       # Frontend
├── docs/
├── tests/
├── config/
└── ...
```

**Migration:** Update any scripts with hardcoded paths.

### 4. Docker Compose Files

**Before (v0.2):**
- `docker-compose.yml` - Basic stack
- `docker-compose.full.yml` - Full stack

**After (v0.3):**
- `docker-compose.yml` - Full stack (primary)
- `docker-compose.minimal.yml` - Basic stack (archived)

**Migration:** Use `docker-compose up` instead of `docker-compose -f docker-compose.full.yml up`

### 5. Volume Mounts

If you have custom docker-compose.override.yml:

**Before:**
```yaml
volumes:
  - ./hie:/app/hie
  - ./portal:/app/portal
```

**After:**
```yaml
volumes:
  - ./Engine:/app/Engine
  - ./Portal:/app/Portal
```

## Step-by-Step Migration

### For Developers

1. **Pull latest changes:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Reinstall package:**
   ```bash
   pip uninstall hie
   pip install -e ".[dev]"
   ```

3. **Update your code:**
   - Run find/replace: `from hie.` → `from Engine.`
   - Update any custom scripts

4. **Rebuild Docker images:**
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

5. **Run tests:**
   ```bash
   pytest tests/
   ```

### For Production Deployments

1. **Backup data volumes:**
   ```bash
   docker-compose down
   docker run --rm -v hie_postgres_data:/data -v $(pwd):/backup \
     alpine tar czf /backup/postgres_backup.tar.gz -C /data .
   ```

2. **Update deployment configs:**
   - Update service names in orchestration tools
   - Update environment variables
   - Update volume mount paths

3. **Deploy new version:**
   ```bash
   git pull origin v0.3.0
   docker-compose pull
   docker-compose up -d
   ```

4. **Verify services:**
   ```bash
   curl http://localhost:9300/health  # Engine
   curl http://localhost:9302/api/health  # Manager
   curl http://localhost:9303  # Portal
   ```

## What Hasn't Changed

✅ **Package name**: Still install with `pip install hie`
✅ **CLI command**: Still use `hie` command
✅ **API endpoints**: Same REST endpoints
✅ **Database schema**: No database migrations needed
✅ **Configuration format**: YAML/JSON configs unchanged
✅ **Port mapping**: Same ports (9300-9350 range)
✅ **Default credentials**: Same admin credentials

## Common Issues & Solutions

### Issue: Import errors after upgrade

**Error:**
```
ModuleNotFoundError: No module named 'hie'
```

**Solution:**
```bash
pip uninstall hie
pip install -e ".[dev]"
```

### Issue: Docker build fails

**Error:**
```
COPY failed: file not found in build context
```

**Solution:**
Rebuild images from scratch:
```bash
docker-compose down -v
docker system prune -af
docker-compose build --no-cache
```

### Issue: Portal can't connect to API

**Error:**
```
Failed to fetch: http://hie-api:8081
```

**Solution:**
Update environment variable:
```bash
# In docker-compose.yml or .env
NEXT_PUBLIC_API_URL=http://hie-manager:8081
```

### Issue: Tests fail with import errors

**Error:**
```
ImportError: cannot import name 'Message' from 'hie.core.message'
```

**Solution:**
Update test imports:
```bash
find tests -name "*.py" -exec sed -i '' 's/from hie\./from Engine\./g' {} \;
```

## Rollback Plan

If issues occur:

```bash
# Stop current version
docker-compose down

# Checkout previous version
git checkout v0.2.0

# Restore volumes if needed
docker run --rm -v hie_postgres_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /data

# Start previous version
docker-compose -f docker-compose.full.yml up -d
```

## Support

If you encounter issues not covered in this guide:
1. Check that all Python imports are updated
2. Check that Docker images are rebuilt
3. Check that volume mounts use new paths
4. Check that service names are updated in configs

For additional help, see:
- [README.md](../README.md) - Updated project documentation
- [CHANGELOG.md](../CHANGELOG.md) - Detailed change log
- GitHub Issues - Report problems

## Verification Checklist

After migration, verify:
- [ ] `pip install -e .` succeeds
- [ ] `hie --help` works
- [ ] Imports work: `python -c "from Engine.core.message import Message"`
- [ ] Docker builds: `docker-compose build`
- [ ] Services start: `docker-compose up -d`
- [ ] Health checks pass (9300, 9302, 9303)
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Portal loads at http://localhost:9303
- [ ] API responds at http://localhost:9302/api/health
