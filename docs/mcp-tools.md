# FastMCP Tools & Resources Reference

SpendWise exposes 7 specialized financial management tools and 1 dynamic resource over the Model Context Protocol (MCP).

---

## 🛠️ Tool Catalog

### 1. `add_expense`
Records a new financial expense in the SQLite database.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `amount` | `number` | Yes | Monetary value of the expense (> 0) |
| `category` | `string` | Yes | General category (e.g. Food, Transportation, Housing) |
| `subcategory` | `string` | No | Optional subcategory (e.g. Groceries, Dining, Taxi) |
| `note` | `string` | No | Optional description or details |
| `date` | `string` | No | Date in `YYYY-MM-DD` format (defaults to current date) |

---

### 2. `update_expense`
Modifies an existing expense record by ID.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `expense_id` | `integer` | Yes | ID of the expense to update |
| `amount` | `number` | No | New monetary amount |
| `category` | `string` | No | New category |
| `subcategory` | `string` | No | New subcategory |
| `note` | `string` | No | New description |
| `date` | `string` | No | New date in `YYYY-MM-DD` |

---

### 3. `delete_expense`
Deletes an expense from the database by its unique identifier.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `expense_id` | `integer` | Yes | The ID of the expense to remove |

---

### 4. `list_expenses`
Queries and filters recorded transactions from the ledger.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start_date` | `string` | No | Start date filter (`YYYY-MM-DD`) |
| `end_date` | `string` | No | End date filter (`YYYY-MM-DD`) |
| `category` | `string` | No | Filter by category |
| `subcategory` | `string` | No | Filter by subcategory |
| `limit` | `integer` | No | Max items to return (default: 20) |

---

### 5. `summarize`
Aggregates expenses grouped by category, subcategory, or month.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `by` | `string` | No | Grouping field: `"category"`, `"subcategory"`, or `"month"` |
| `month` | `string` | No | Filter by specific month (`YYYY-MM`) |
| `year` | `string` | No | Filter by specific year (`YYYY`) |

---

### 6. `set_budget`
Sets or updates a monthly spending limit for a specific category.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `category` | `string` | Yes | Category name (e.g. Food, Entertainment) |
| `limit_amount` | `number` | Yes | Monthly spending limit |

---

### 7. `check_budget`
Compares actual spending against monthly budget limits and reports remaining allowances.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `month` | `string` | No | Target month (`YYYY-MM`), defaults to current month |

---

## 📦 Dynamic Resources

### `categories://list`
- **MIME Type**: `application/json`
- **Description**: Returns the taxonomy of allowed general categories and subcategories from `mcp/categories.json`.
- **Usage**: Injected into the agent's system prompt at session initialization so the LLM categorizes transactions without extra tool roundtrips.
