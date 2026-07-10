# Power BI Dashboard Build Instructions (Phase 7)

This guide walks you through building the Power BI dashboard from the processed CSVs we just generated. Because Power BI Desktop cannot be scripted by code, you will need to perform these steps manually.

## 1. Import the Data

1. Open **Power BI Desktop**.
2. Start a new file and save it as `powerbi/retail_dashboard.pbix`.
3. On the Home ribbon, click **Get Data** -> **Text/CSV**.
4. Navigate to your project folder: `data/processed/` and select `Dim_Date.csv`.
5. **IMPORTANT:** Click **Transform Data** (not Load). This opens the Power Query Editor.
6. In Power Query Editor, verify the data types:
   - For `Dim_Date`, ensure `full_date` is set to **Date** type.
7. Click **New Source** -> **Text/CSV** and repeat this for the remaining four files:
   - `Dim_Product.csv`
   - `Dim_Region.csv`
   - `Dim_Customer.csv`
   - `Fact_Sales.csv`
8. For `Fact_Sales`, ensure these columns are set to **Decimal Number**:
   - `gross_revenue`, `net_revenue`, `cost`, `profit`, `margin_pct`, `unit_price`, `discount_pct`.
9. Ensure these columns are set to **Whole Number**:
   - `quantity`, `returned_flag`, all `_id` columns.
10. Click **Close & Apply** on the Home ribbon to load the data into the model.

## 2. Build the Star Schema Relationships

1. Click the **Model view** icon on the left sidebar (the network diagram icon).
2. Drag and drop the ID fields to create relationships between the dimension tables and `Fact_Sales`:
   - Drag `Dim_Date[date_id]` to `Fact_Sales[date_id]`
   - Drag `Dim_Product[product_key]` to `Fact_Sales[product_id]`
   - Drag `Dim_Region[region_id]` to `Fact_Sales[region_id]`
   - Drag `Dim_Customer[customer_id]` to `Fact_Sales[customer_id]`
3. Double-click each connecting line to verify the properties:
   - **Cardinality:** 1 to Many (1 on the Dimension side, * on the Fact side).
   - **Cross filter direction:** Single.
4. *Best Practice:* Hide the foreign key columns in `Fact_Sales` from the Report view. (Right-click `date_id`, `product_id`, etc. in `Fact_Sales` and click **Hide in report view**).

## 3. Mark the Date Table

*This step is mandatory for the DAX time-intelligence functions to work.*

1. Go to the **Data view** (the table icon on the left).
2. Select the `Dim_Date` table from the Fields pane on the right.
3. On the Table tools ribbon, click **Mark as Date Table** -> **Mark as Date Table**.
4. In the dialog box, select `full_date` as the Date column. It will say "Validated successfully". Click OK.

## 4. Add the DAX Measures

1. Open the `dax/measures.dax` file we generated in Phase 6.
2. In Power BI, right-click the `Fact_Sales` table in the Fields pane and click **New Measure**.
3. Copy the formula for `Total Revenue` and paste it into the formula bar. Press Enter.
4. Select the new measure, go to the Measure tools ribbon, and set the format (e.g., Currency, $).
5. Repeat this process for all 8 measures.
   - For percentages (`Margin %`, `Revenue YoY`, `Return Rate`), set the format to **Percentage**.

## 5. Build the Report Pages

Create 4 pages using the plus icon at the bottom of the canvas.

### Page 1: Executive Summary
- **KPI Cards (4):** Use the Card visual to display `Total Revenue`, `Total Profit`, `Margin %`, and `Revenue YoY`.
- **Trend Chart:** Add a Line Chart.
  - X-axis: `Dim_Date[full_date]` (or Year/Month hierarchy).
  - Y-axis: `Total Revenue`.
  - Secondary Y-axis (or add as second line): `Rolling 30-Day Revenue` to show the smoothed trend.

### Page 2: Region Deep-Dive
- **Bar Chart:** Total Revenue by `Dim_Region[region_name]`.
- **Matrix Visual:** 
  - Rows: `Dim_Region[region_name]`
  - Columns: `Dim_Product[category]`
  - Values: `Total Revenue` and `Margin %`

### Page 3: Inventory Health
- **Table Visual:** 
  - Columns: `Dim_Product[category]`, `Dim_Product[sub_category]`, `Dim_Region[region_name]`, `Margin %`, `Return Rate`, `Underperformer Flag`.
- **Sort:** Click the `Margin %` column header to sort ascending (worst margins at the top).
- **Conditional Formatting:** Right-click `Margin %` in the visual fields pane -> Conditional Formatting -> Background color. Set it to color-code red for low/negative values.
- *Verify:* You should see Furniture -> Tables -> South at the top flagged as "Underperforming".

### Page 4: Recommendations
- Add a **Text Box** summarizing the findings. Example:
  > **Supply Chain Action Required:** 
  > The Furniture category in the South region (specifically Tables) is severely underperforming with a margin of -12% and an abnormal return rate of 21%. 
  > 
  > **Recommendation:** Suspend automatic reorders for Tables in the South warehouse (`WH-008`), review supplier quality with WoodCraft Furnishings, and limit future discounting rules in this region to prevent further margin erosion.

## 6. Export Screenshots
Once the dashboard looks professional and polished, use Snipping Tool (Win+Shift+S) to capture each page. Save them in the `screenshots/` directory (e.g., `executive_summary.png`, `inventory_health.png`). These will be displayed in the README.
