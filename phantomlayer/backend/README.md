# PhantomLayer Backend

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Database Setup (Phase 2)

Start the PostgreSQL databases using Docker:

```bash
# From project root
docker run -d --name phantomlayer-postgres-real \
  -e POSTGRES_USER=phantomlayer \
  -e POSTGRES_PASSWORD=phantomlayer \
  -e POSTGRES_DB=phantomlayer_real \
  -p 5432:5432 \
  -v postgres_real_data:/var/lib/postgresql/data \
  postgres:16-alpine

docker run -d --name phantomlayer-postgres-honeypot \
  -e POSTGRES_USER=phantomlayer \
  -e POSTGRES_PASSWORD=phantomlayer \
  -e POSTGRES_DB=phantomlayer_honeypot \
  -p 5433:5432 \
  -v postgres_honeypot_data:/var/lib/postgresql/data \
  postgres:16-alpine
```

Or use docker-compose (if available):
```bash
docker-compose up -d
```

Copy the environment example:
```bash
cp ../.env.example .env
```

## Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
pytest
```

Or with verbose output:

```bash
pytest -v
```

## Health Check

Once the server is running, test the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "PhantomLayer"
}
```

## Database Configuration

Two separate PostgreSQL databases are configured:

1. **Real Database** (production data):
   - Host: localhost:5432
   - Database: phantomlayer_real
   - URL: `postgresql+psycopg://phantomlayer:phantomlayer@localhost:5432/phantomlayer_real`

2. **Honeypot Database** (deceptive data):
   - Host: localhost:5433
   - Database: phantomlayer_honeypot
   - URL: `postgresql+psycopg://phantomlayer:phantomlayer@localhost:5433/phantomlayer_honeypot`

Environment variables:
- `REAL_DATABASE_URL`
- `HONEYPOT_DATABASE_URL`

Both databases use separate connection pools and SQLAlchemy engines.

## PhantomLayer Gateway (Phase 4)

The PhantomLayer Gateway is the core routing layer that sits between clients and the two databases:

```
Client/Application
        |
        v
PhantomLayer Gateway
        |
        +------> Real Database (port 5432)
        |
        +------> Honeypot Database (port 5433)
```

### Why the Gateway Exists

The gateway provides a unified interface for accessing both databases while maintaining strict isolation. It enables:

- **Explicit routing**: Clients choose which database to query (`real` or `honeypot`)
- **Structured operations**: Only predefined, safe operations are allowed (no arbitrary SQL)
- **Clear target identification**: Every response identifies which database was used
- **Foundation for future phases**: Detection engine, risk scoring, and automatic routing will build on this

### REAL vs HONEYPOT Targets

| Target | Description | Database |
|--------|-------------|----------|
| `real` | Legitimate production data | `phantomlayer_real` (port 5432) |
| `honeypot` | Deceptive/decoy data | `phantomlayer_honeypot` (port 5433) |

**Important**: Both databases have identical schema structure but completely different data. No data is shared between them.

### Current Behavior: Explicit Routing Only

**Phase 4 implements manual/explicit routing only**. The client specifies the target in each request. There is NO:
- Automatic attack detection
- Suspicious query detection
- Machine learning / AI
- Risk scoring
- Automatic honeypot routing
- Security decisions

These features will be implemented in later phases (Phase 5+).

### Gateway Endpoints

#### GET /gateway/health
Checks connectivity to both databases.

```bash
curl http://localhost:8000/gateway/health
```

Response:
```json
{
  "gateway": "PhantomLayer Gateway",
  "status": "healthy",
  "real_database": "healthy",
  "honeypot_database": "healthy"
}
```

#### POST /gateway/query
Executes a structured operation against the specified target.

```bash
curl -X POST http://localhost:8000/gateway/query \
  -H "Content-Type: application/json" \
  -d '{
    "target": "real",
    "operation": "get_users"
  }'
```

**Request body:**
```json
{
  "target": "real|honeypot",
  "operation": "health_check|list_tables|get_users|get_customers|get_products|get_orders",
  "parameters": {}
}
```

**Supported operations:**
- `health_check` - Verify database connectivity (returns `{"health": 1}`)
- `list_tables` - List all tables in the database
- `get_users` - Fetch users (with optional `limit`, `offset` parameters)
- `get_customers` - Fetch customers (with optional `limit`, `offset` parameters)
- `get_products` - Fetch products (with optional `limit`, `offset` parameters)
- `get_orders` - Fetch orders (with optional `limit`, `offset` parameters)

**Response:**
```json
{
  "target": "real",
  "operation": "get_users",
  "success": true,
  "data": [
    {"id": 1, "username": "admin", "email": "admin@phantomlayer.demo", "role": "ADMIN", "is_active": true, "created_at": "..."},
    ...
  ],
  "error": null,
  "row_count": 4
}
```

### Example API Requests

**Get users from REAL database:**
```bash
curl -X POST http://localhost:8000/gateway/query \
  -H "Content-Type: application/json" \
  -d '{"target": "real", "operation": "get_users"}'
```

**Get users from HONEYPOT database:**
```bash
curl -X POST http://localhost:8000/gateway/query \
  -H "Content-Type: application/json" \
  -d '{"target": "honeypot", "operation": "get_users"}'
```

**Get products with pagination:**
```bash
curl -X POST http://localhost:8000/gateway/query \
  -H "Content-Type: application/json" \
  -d '{"target": "real", "operation": "get_products", "parameters": {"limit": 5, "offset": 0}}'
```

**List tables:**
```bash
curl -X POST http://localhost:8000/gateway/query \
  -H "Content-Type: application/json" \
  -d '{"target": "real", "operation": "list_tables"}'
```

### Error Handling

Invalid target returns 422:
```bash
curl -X POST http://localhost:8000/gateway/query \
  -H "Content-Type: application/json" \
  -d '{"target": "invalid", "operation": "get_users"}'
```

Invalid operation returns 422:
```bash
curl -X POST http://localhost:8000/gateway/query \
  -H "Content-Type: application/json" \
  -d '{"target": "real", "operation": "drop_table"}'
```

### Running Gateway Tests

```bash
pytest tests/test_gateway.py -v
```

Or run all tests:
```bash
pytest -v
```

### Security Notes

- **No arbitrary SQL execution**: Only predefined operations are allowed
- **No shell/command execution**: Gateway only executes parameterized SQL queries
- **No credential exposure**: Database credentials are never returned
- **Isolated databases**: Real and honeypot databases are completely separate
- **Local development only**: This is a demonstration environment, not production-ready

## PhantomLayer Detection Engine (Phase 5)

The Detection Engine analyzes incoming gateway requests and produces a structured security assessment. It does NOT perform routing — it only provides a recommendation.

```
Incoming Request
       |
       v
Detection Engine
       |
       +---- DetectionResult (suspicious, risk_score, severity, triggered_rules, reasons, recommended_target)
       |
       v
[Later Phase: Routing Decision]
       |
       +---- REAL DB
       |
       +---- HONEYPOT DB
```

### Detection Rules

| Rule | Description | Severity | Score | Triggered When |
|------|-------------|----------|-------|----------------|
| `RULE_SENSITIVE_DATA_ACCESS` | Request attempts to access sensitive user/customer data | HIGH | 60 | Operation is `get_users` or `get_customers` |
| `RULE_ENUMERATION` | Request attempts to enumerate database structure | MEDIUM | 30 | Operation is `list_tables` |
| `RULE_INVALID_OPERATION` | Request uses an unknown or invalid operation | HIGH | 50 | Operation not in allowed list |
| `RULE_HONEYPOT_TARGET` | Request explicitly targets the honeypot database | CRITICAL | 80 | Target is `honeypot` |
| `RULE_RECONNAISSANCE` | Reconnaissance operation targeting real database | HIGH | 40 | Operation is `list_tables` AND target is `real` |

### Risk Score & Severity

| Risk Score | Severity | Description |
|------------|----------|-------------|
| 0 | LOW | No suspicious indicators |
| 1-30 | LOW | Minimal risk |
| 31-50 | MEDIUM | Moderate risk (e.g., invalid operation) |
| 51-75 | HIGH | High risk (e.g., sensitive data access) |
| 76-100 | CRITICAL | Critical risk (e.g., honeypot targeting) |

**Risk score calculation**: Sum of triggered rule scores, capped at 100.

### Recommended Target Logic

| Condition | Recommended Target |
|-----------|-------------------|
| Target is `honeypot` | `real` (honeypot targeting is suspicious) |
| Risk score >= 50 | `honeypot` (redirect suspicious traffic) |
| Otherwise | `real` |

### Detection Endpoints

#### GET /detection/health
Checks detection engine status and loaded rules.

```bash
curl http://localhost:8000/detection/health
```

Response:
```json
{
  "service": "PhantomLayer Detection Engine",
  "status": "healthy",
  "rules_loaded": [
    "RULE_SENSITIVE_DATA_ACCESS",
    "RULE_ENUMERATION",
    "RULE_INVALID_OPERATION",
    "RULE_HONEYPOT_TARGET",
    "RULE_RECONNAISSANCE"
  ]
}
```

#### POST /detection/analyze
Analyzes a request and returns a detection result.

```bash
curl -X POST http://localhost:8000/detection/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "target": "real",
    "operation": "get_users"
  }'
```

**Request body:**
```json
{
  "target": "real|honeypot",
  "operation": "health_check|list_tables|get_users|get_customers|get_products|get_orders",
  "parameters": {},
  "client_ip": "optional",
  "user_agent": "optional"
}
```

**Response:**
```json
{
  "suspicious": true,
  "risk_score": 60,
  "severity": "HIGH",
  "triggered_rules": [
    {
      "rule": "RULE_SENSITIVE_DATA_ACCESS",
      "description": "Request attempts to access sensitive user or customer data",
      "severity": "HIGH",
      "score": 60
    }
  ],
  "reasons": [
    "Operation 'get_users' accesses sensitive data (users/customers)"
  ],
  "recommended_target": "honeypot"
}
```

### Example Detection Results

**Normal Request (health_check):**
```json
{
  "suspicious": false,
  "risk_score": 0,
  "severity": "LOW",
  "triggered_rules": [],
  "reasons": [],
  "recommended_target": "real"
}
```

**Sensitive Data Access (get_users):**
```json
{
  "suspicious": true,
  "risk_score": 60,
  "severity": "HIGH",
  "triggered_rules": [
    {
      "rule": "RULE_SENSITIVE_DATA_ACCESS",
      "description": "Request attempts to access sensitive user or customer data",
      "severity": "HIGH",
      "score": 60
    }
  ],
  "reasons": ["Operation 'get_users' accesses sensitive data (users/customers)"],
  "recommended_target": "honeypot"
}
```

**Multiple Rules (list_tables on real):**
```json
{
  "suspicious": true,
  "risk_score": 70,
  "severity": "HIGH",
  "triggered_rules": [
    {
      "rule": "RULE_ENUMERATION",
      "description": "Request attempts to enumerate database structure",
      "severity": "MEDIUM",
      "score": 30
    },
    {
      "rule": "RULE_RECONNAISSANCE",
      "description": "Reconnaissance operation targeting real database",
      "severity": "HIGH",
      "score": 40
    }
  ],
  "reasons": [
    "Operation 'list_tables' performs database enumeration",
    "Reconnaissance operation 'list_tables' directed at real database"
  ],
  "recommended_target": "honeypot"
}
```

**Honeypot Targeting:**
```json
{
  "suspicious": true,
  "risk_score": 80,
  "severity": "CRITICAL",
  "triggered_rules": [
    {
      "rule": "RULE_HONEYPOT_TARGET",
      "description": "Request explicitly targets the honeypot database",
      "severity": "CRITICAL",
      "score": 80
    }
  ],
  "reasons": ["Target is 'honeypot' - attacker may be probing deception infrastructure"],
  "recommended_target": "real"
}
```

### Running Detection Tests

```bash
pytest tests/test_detection.py -v
```

Or run all tests:
```bash
pytest -v
```

### Current Limitations

- **No automatic routing**: Detection result is advisory only; gateway still requires explicit target
- **No request history**: Repeated access patterns (RULE_REPEATED_ACCESS) not yet implemented — requires session/context tracking
- **No ML/AI**: Rules are deterministic and explainable; no anomaly detection yet
- **Static rule set**: Rules are hardcoded; no dynamic rule loading
- **No integration with gateway**: Detection runs separately; Phase 6+ will integrate routing decisions

These limitations will be addressed in future phases.

## PhantomLayer Risk Scoring Engine (Phase 6)

The Risk Scoring Engine provides a clean risk-assessment layer between detection and the automatic routing system. It combines triggered detection rules into a weighted risk score with confidence metrics.

```
Detection Engine
       |
       v
Triggered Rules
       |
       v
Risk Scoring Engine
       |
       v
Risk Assessment (risk_score, severity, confidence, recommended_target)
       |
       v
[Phase 7: Automatic Smart Routing]
```

### Risk Scoring Method: Deterministic Weighted Scoring

The engine uses a deterministic weighted formula:

**Rule Weights** (rule importance):
- `RULE_HONEYPOT_TARGET`: 1.0 (most critical)
- `RULE_SENSITIVE_DATA_ACCESS`: 0.9
- `RULE_RECONNAISSANCE`: 0.85
- `RULE_INVALID_OPERATION`: 0.8
- `RULE_ENUMERATION`: 0.7
- `RULE_REPEATED_ACCESS`: 0.75

**Severity Weights** (amplifies high-severity rules):
- `CRITICAL`: 1.0
- `HIGH`: 0.85
- `MEDIUM`: 0.6
- `LOW`: 0.3

**Weighted Score Formula**:
```
combined_weight = (rule_weight + severity_weight) / 2
weighted_score = base_score * combined_weight

risk_score = Σ(weighted_score * combined_weight) / Σ(combined_weight)
           capped at 100
```

### Confidence Calculation

Confidence is **deterministic** and represents how strongly the available evidence supports the detection (NOT statistical/ML confidence).

```
confidence = 0.25 * (num_rules / 5 capped at 1.0) +
             0.35 * (max_severity_rank / 3) +
             0.20 * avg_rule_weight +
             0.20 * (num_reasons / 5 capped at 1.0)
```

| Confidence Range | Level |
|------------------|-------|
| 0.00 - 0.39 | LOW |
| 0.40 - 0.64 | MEDIUM |
| 0.65 - 0.84 | HIGH |
| 0.85 - 1.00 | VERY_HIGH |

### Risk Score & Severity

| Risk Score | Severity |
|------------|----------|
| 0 | LOW |
| 1-30 | LOW |
| 31-50 | MEDIUM |
| 51-75 | HIGH |
| 76-100 | CRITICAL |

### Recommended Target Logic

| Condition | Recommended Target |
|-----------|-------------------|
| Target is `honeypot` | `real` (honeypot targeting is suspicious) |
| Risk score >= 50 | `honeypot` (redirect suspicious traffic) |
| Otherwise | `real` |

### Risk Endpoints

#### GET /risk/health
```bash
curl http://localhost:8000/risk/health
```

Response:
```json
{
  "service": "PhantomLayer Risk Scoring Engine",
  "status": "healthy",
  "scoring_method": "deterministic_weighted",
  "confidence_thresholds": {
    "LOW": 0.0,
    "MEDIUM": 0.4,
    "HIGH": 0.65,
    "VERY_HIGH": 0.85
  }
}
```

#### POST /risk/assess
```bash
curl -X POST http://localhost:8000/risk/assess \
  -H "Content-Type: application/json" \
  -d '{
    "target": "real",
    "operation": "get_users"
  }'
```

**Response:**
```json
{
  "risk_score": 52,
  "severity": "HIGH",
  "confidence": 0.498,
  "confidence_level": "MEDIUM",
  "triggered_rules": [
    {
      "rule": "RULE_SENSITIVE_DATA_ACCESS",
      "description": "Request attempts to access sensitive user or customer data",
      "severity": "HIGH",
      "base_score": 60,
      "weighted_score": 52,
      "weight": 0.875
    }
  ],
  "reasons": ["Operation 'get_users' accesses sensitive data (users/customers)"],
  "recommended_target": "honeypot",
  "scoring_method": "deterministic_weighted"
}
```

### Running Risk Tests

```bash
pytest tests/test_risk.py -v
```

Or run all tests:
```bash
pytest -v
```

## PhantomLayer Automatic Smart Routing (Phase 7)

The Automatic Smart Routing layer combines Detection Engine + Risk Scoring Engine + Gateway to automatically route requests to either the REAL or HONEYPOT database based on risk assessment.

```
Incoming Request
       |
       v
Detection Engine
       |
       v
Risk Scoring Engine
       |
       v
Routing Decision
       |
       v
Gateway Service (executes on selected target)
       |
       v
Response with routing decision + result
```

### Architecture

```
Routing Service
 ├── Detection Engine (analyzes request)
 ├── Risk Scoring Engine (assesses risk)
 └── Gateway Service (executes on selected database)
```

**Dependency Direction**: Routing depends on Detection, Risk, and Gateway — NOT the reverse.

### Routing Policy

The routing decision uses the Risk Engine's recommendation as the primary factor, with additional safeguards:

| Scenario | Final Target | Reasoning |
|----------|--------------|-----------|
| Low risk (health_check, get_products, get_orders) | REAL | Original target preserved |
| Sensitive data access (get_users, get_customers) | HONEYPOT | Automatically redirected |
| Reconnaissance (list_tables on REAL) | HONEYPOT | Automatically redirected |
| High risk (score >= 50) | HONEYPOT | Risk assessment recommendation |
| Explicit honeypot target | HONEYPOT | Preserve original intent |
| Invalid operation | HONEYPOT | Rejected safely |

The routing service **never**:
- Modifies the real database unexpectedly
- Copies data from REAL into HONEYPOT
- Exposes real database credentials
- Executes arbitrary SQL
- Creates recursive routing loops
- Bypasses the existing GatewayService

### Routing Endpoints

#### GET /routing/health
```bash
curl http://localhost:8000/routing/health
```

Response:
```json
{
  "service": "PhantomLayer Automatic Routing",
  "status": "healthy",
  "routing_policy": "risk_based_automatic",
  "detection_rules_active": 5,
  "risk_scoring_active": true,
  "real_database": "healthy",
  "honeypot_database": "healthy"
}
```

#### POST /routing/route
```bash
curl -X POST http://localhost:8000/routing/route \
  -H "Content-Type: application/json" \
  -d '{
    "target": "real",
    "operation": "get_users"
  }'
```

**Request body:**
```json
{
  "target": "real|honeypot",
  "operation": "health_check|list_tables|get_users|get_customers|get_products|get_orders",
  "parameters": {}
}
```

**Response:**
```json
{
  "original_target": "real",
  "final_target": "honeypot",
  "operation": "get_users",
  "risk_score": 52,
  "severity": "HIGH",
  "confidence": 0.498,
  "confidence_level": "MEDIUM",
  "suspicious": true,
  "triggered_rules": [
    {
      "rule": "RULE_SENSITIVE_DATA_ACCESS",
      "description": "Request attempts to access sensitive user or customer data",
      "severity": "HIGH",
      "base_score": 60,
      "weighted_score": 52,
      "weight": 0.875
    }
  ],
  "reasons": ["Operation 'get_users' accesses sensitive data (users/customers)"],
  "routing_decision": "routed_to_honeypot",
  "routing_reason": "Sensitive data access (get_users). Automatically routed to HONEYPOT. Risk score: 52.",
  "gateway_result": [
    {"id": 1, "username": "sysadmin", "email": "sysadmin@deception.local", ...}
  ],
  "gateway_success": true,
  "gateway_error": null
}
```

### Example Routing Scenarios

**Normal Request (health_check):**
```json
{
  "original_target": "real",
  "final_target": "real",
  "risk_score": 0,
  "severity": "LOW",
  "routing_decision": "original_target_preserved",
  "routing_reason": "Low risk request (score: 0). Original target REAL preserved."
}
```

**Sensitive Data Access (get_users on REAL):**
```json
{
  "original_target": "real",
  "final_target": "honeypot",
  "risk_score": 52,
  "severity": "HIGH",
  "routing_decision": "routed_to_honeypot",
  "routing_reason": "Sensitive data access (get_users). Automatically routed to HONEYPOT. Risk score: 52."
}
```

**Reconnaissance (list_tables on REAL):**
```json
{
  "original_target": "real",
  "final_target": "honeypot",
  "risk_score": 27,
  "severity": "LOW",
  "routing_decision": "routed_to_honeypot",
  "routing_reason": "Reconnaissance operation (list_tables on REAL). Automatically routed to HONEYPOT. Risk score: 27."
}
```

**Explicit Honeypot Target:**
```json
{
  "original_target": "honeypot",
  "final_target": "honeypot",
  "risk_score": 80,
  "severity": "CRITICAL",
  "routing_decision": "routed_to_honeypot",
  "routing_reason": "Explicit honeypot target. Request executed on HONEYPOT. Risk score: 80."
}
```

**Invalid Operation:**
```json
{
  "original_target": "real",
  "final_target": "real",
  "risk_score": 41,
  "severity": "MEDIUM",
  "routing_decision": "routed_to_honeypot",
  "routing_reason": "Invalid operation 'drop_table'. Request rejected.",
  "gateway_success": false,
  "gateway_error": "Unsupported operation: drop_table"
}
```

### Running Routing Tests

```bash
pytest tests/test_routing.py -v
```

Or run all tests:
```bash
pytest -v
```

### Security Notes

- **No arbitrary SQL execution**: Only predefined operations are allowed
- **No shell/command execution**: Gateway only executes parameterized SQL queries
- **No credential exposure**: Database credentials are never returned
- **Isolated databases**: Real and honeypot databases are completely separate
- **Local development only**: This is a demonstration environment, not production-ready