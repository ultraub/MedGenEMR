# CLAUDE.md - MedGenEMR Quick Reference

**Status**: FHIR-Native EMR | React + FastAPI | PostgreSQL  
**Updated**: 2025-01-05  

## 🚀 Quick Start

```bash
# Start system
./start.sh

# Common issues
docker-compose down -v  # Reset if errors
cd frontend && npm install  # Fix missing deps
```

## ⛔ Critical Rules

### 1. Data Requirements
**DO**:
- ✅ Use ONLY Synthea-generated FHIR data
- ✅ Test with multiple patients  
- ✅ Handle missing/null data gracefully

**DON'T**:
- ❌ Create test patients (John Doe, etc.)
- ❌ Hardcode IDs or mock data
- ❌ Use array indexes for data access

### 2. Implementation Standards  
**DO**:
- ✅ Complete ALL features end-to-end
- ✅ Implement error handling & loading states
- ✅ Follow existing component patterns

**DON'T**:
- ❌ Leave TODOs or console.log() placeholders
- ❌ Skip validation or error cases
- ❌ Create partial implementations

### 3. Development Process
**DO**:
- ✅ Check TodoRead before starting
- ✅ Review PROJECT_INTEGRITY_GUIDE.md for errors
- ✅ Update TodoWrite frequently  

**DON'T**:
- ❌ Skip documentation updates
- ❌ Ignore build file validation after 3+ changes
- ❌ Commit without user request

### 4. File Creation Standards
**DO**:
- ✅ Use Unix line endings (LF) for all scripts
- ✅ Set executable permissions: `chmod +x script.sh`
- ✅ Test scripts on macOS/Linux before committing

**DON'T**:
- ❌ Create files with Windows line endings (CRLF)
- ❌ Use `\r\n` line endings in shell scripts
- ❌ Skip testing executable scripts

## 📍 Current State

- **Frontend**: 12 FHIR-native components in `/src/components/clinical/`
- **Backend**: FHIR R4 API at `/fhir/R4/`, data in `fhir` schema
- **Resources**: 3,461 Synthea FHIR resources available
- **Recent Fix**: fhirClient returns `resources` array, not `entry`

## 🔧 Common Tasks

### Fix Data Display Issues
```javascript
// ✅ CORRECT - fhirClient format
const result = await fhirClient.search('Condition', {patient: id});
const conditions = result.resources || [];  // NOT result.entry

// ✅ CORRECT - Render FHIR objects safely  
<Typography>
  {condition.code?.text || condition.code?.coding?.[0]?.display || 'Unknown'}
</Typography>
```

### Add New Component
1. Create in `/src/components/clinical/`
2. Use hooks from `/src/hooks/useFHIRResources.js`
3. Follow pattern from `PatientDashboardV3.js`
4. Update `FRONTEND_REDESIGN_TRACKER.md`

### Handle Icon Imports
```javascript
// ✅ CORRECT
import { Warning as WarningIcon } from '@mui/icons-material';
// ❌ WRONG  
import { Warning as WarningIcon } from '@mui/material';
```

## 🐛 Error Quick Fixes

| Error | Fix |
|-------|-----|
| `export 'X' not found` | Import from `@mui/icons-material` |
| `Objects are not valid as React child` | Extract text: `obj?.text \|\| obj?.coding?.[0]?.display` |
| `conditions.filter is not a function` | Use `conditions.activeConditions` |
| Missing clinical data | Check `fhir` schema, use `result.resources` |
| `bad interpreter: /bin/bash^M` | Fix line endings: `sed -i '' 's/\r$//' script.sh` |
| Pillow build fails on Python 3.13 | Use `pillow>=10.3.0` in requirements.txt |
| asyncpg build fails on Python 3.13 | Use `asyncpg>=0.30.0` in requirements.txt |
| cmake not found for pylibjpeg | Install cmake: `brew install cmake` |
| pylibjpeg-openjpeg CMake error | Comment out `pylibjpeg-openjpeg` in requirements.txt |

## 📁 Key Files

- **Hooks**: `/src/hooks/useFHIRResources.js`
- **Context**: `/src/contexts/FHIRResourceContext.js`
- **Components**: `/src/components/clinical/`
- **Error Patterns**: `PROJECT_INTEGRITY_GUIDE.md`
- **API Reference**: `docs/API_ENDPOINTS.md`

## 🧪 Testing

```bash
# Backend FHIR tests
docker exec emr-backend pytest tests/test_fhir_endpoints.py -v

# Generate Synthea data (max 5 patients)
cd backend && python scripts/synthea_workflow.py full --count 5

# Debug data issues
- Add console.log to see actual data structure
- Check browser console for FHIR object rendering
- Verify API returns data: http://localhost:8000/fhir/R4/Patient
```

## 📋 Session Checklist

**Before Starting**:
- [ ] Run TodoRead
- [ ] Check PROJECT_INTEGRITY_GUIDE.md
- [ ] Verify system running: `./start.sh`

**During Work**:
- [ ] Use Synthea data only
- [ ] Test with multiple patients
- [ ] Update TodoWrite on progress

**After Changes**:
- [ ] All features fully implemented
- [ ] No console errors
- [ ] Update relevant docs
- [ ] Run build validation if 3+ files changed