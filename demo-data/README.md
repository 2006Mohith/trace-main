# TRACE Demo Data — Andhra Pradesh / Telangana Scenarios
# Case Files for Regional Crime Investigations — June 2026

This directory contains simulated CDR (Call Detail Record) and IPDR (Internet Protocol Detail Record) data structured exactly according to standard telecom operator export templates used in TRACE. All coordinates are strictly within Andhra Pradesh and Telangana jurisdictions (bounded by Lat 12.6°N to 19.9°N, Lon 76.7°E to 84.8°E).

---

## 📂 Case 1: Ongole Tobacco Smuggling Syndicate (FIR 124/2026)
*Jurisdiction: Prakasham District, Andhra Pradesh*

### Suspect Profiles & Files
* **Kalyan Chakravarthy** (Primary Suspect - Kingpin)
  * CDR: `Case1_Ongole_Tobacco_Smuggling_CDR_Kalyan_Chakravarthy.csv`
  * IPDR: `Case1_Ongole_Tobacco_Smuggling_IPDR_Kalyan_Chakravarthy.csv`
* **Venkatesh Prasad** (Co-conspirator - Transport coordinator)
  * CDR: `Case1_Ongole_Tobacco_Smuggling_CDR_Venkatesh_Prasad.csv`
  * IPDR: `Case1_Ongole_Tobacco_Smuggling_IPDR_Venkatesh_Prasad.csv`
* **Subba Rao** (Co-conspirator - Local dealer)
  * CDR: `Case1_Ongole_Tobacco_Smuggling_CDR_Subba_Rao.csv`
* **Ananthakrishna** (Associate/Buyer)
  * CDR: `Case1_Ongole_Tobacco_Smuggling_CDR_Ananthakrishna.csv`
* **Anjali Devi** (Clean control - Negative baseline)
  * CDR: `Case1_Ongole_Tobacco_Smuggling_CDR_Anjali_Devi.csv`

### Analytics Findings (Case 1)
1. **IMEI Swap:** Kalyan Chakravarthy swaps his phone from old IMEI `359876123400001` to new IMEI `490876123499999` on Day 3 (June 3rd) at 02:30 AM.
2. **Co-location:** Kalyan, Venkatesh, and Subba Rao co-locate at Chirala Prakasham tower (`TWR-CDD-001`) on Day 2 (June 2nd) around 15:00 - 15:15.
3. **Common Contact:** Kalyan, Venkatesh, and Subba Rao all communicate with the same common handler number: `919888000111` (Venkata Ramana).
4. **Behavioral Anomaly:** Kalyan's profile is flagged as an outlier (anomaly score) due to burst call volumes on Day 1-2, immediate silence on Day 4, and high night calling ratio (>70%).
5. **OTT Usage:** IPDR traffic maps Kalyan's device to WhatsApp (`157.240.198.35`) and Telegram (`149.154.167.91`) secure app servers.

---

## 📂 Case 2: Hyderabad–Guntur Cyber Fraud Network (FIR 135/2026)
*Jurisdiction: Telangana & Andhra Pradesh*

### Suspect Profiles & Files
* **Ranga Reddy** (Primary Suspect - Fraud Operator)
  * CDR: `Case2_Hyd_Gnt_Cyber_Fraud_CDR_Ranga_Reddy.csv`
  * IPDR: `Case2_Hyd_Gnt_Cyber_Fraud_IPDR_Ranga_Reddy.csv`
* **Srinivas Rao** (Co-conspirator - Money mule manager)
  * CDR: `Case2_Hyd_Gnt_Cyber_Fraud_CDR_Srinivas_Rao.csv`
  * IPDR: `Case2_Hyd_Gnt_Cyber_Fraud_IPDR_Srinivas_Rao.csv`
* **Venkateswara Rao** (Co-conspirator - Tech support)
  * CDR: `Case2_Hyd_Gnt_Cyber_Fraud_CDR_Venkateswara_Rao.csv`
* **Lalitha Prasad** (Clean control - Negative baseline)
  * CDR: `Case2_Hyd_Gnt_Cyber_Fraud_CDR_Lalitha_Prasad.csv`

### Analytics Findings (Case 2)
1. **IMEI Swap:** Ranga Reddy swaps his device IMEI on Day 5 (June 5th) at 04:15 AM.
2. **Co-location:** Ranga, Srinivas, and Venkateswara Rao co-locate at the Hyderabad Secunderabad tower (`TWR-HYD-001`) on Day 3 (June 3rd) around 11:00 - 11:15 AM.
3. **Common Contact:** The three suspects share a common handler contact number `919701000222` (Bhaskara Rao).

---

## 📂 Case 3: Visakhapatnam Port Contraband Ring (FIR 201/2026)
*Jurisdiction: Coastal Andhra Pradesh & Telangana*

### Suspect Profiles & Files
* **Tirupati Naidu** (Primary Suspect - Harbor Operator)
  * CDR: `Case3_Vizag_Contraband_Cartel_CDR_Tirupati_Naidu.csv`
  * IPDR: `Case3_Vizag_Contraband_Cartel_IPDR_Tirupati_Naidu.csv`
* **Madhav Prasad** (Co-conspirator - Transport driver)
  * CDR: `Case3_Vizag_Contraband_Cartel_CDR_Madhav_Prasad.csv`
  * IPDR: `Case3_Vizag_Contraband_Cartel_IPDR_Madhav_Prasad.csv`
* **Satyanarayana** (Clean control - Negative baseline)
  * CDR: `Case3_Vizag_Contraband_Cartel_CDR_Satyanarayana.csv`

### Analytics Findings (Case 3)
1. **IMEI Swap:** Tirupati Naidu swaps his device IMEI on Day 4 (June 4th) at 18:30 PM.
2. **Co-location:** Tirupati and Madhav co-locate at the Vijayawada Central tower (`TWR-VJA-001`) on Day 4 (June 4th) around 18:30 PM.
3. **Common Contact:** Tirupati and Madhav contact the same common handler contact number `919611000333` (Prabhakar Reddy).

---

## 🚀 How to upload to TRACE:
1. Open the TRACE Frontend UI (`http://localhost:5173`).
2. Go to **New Case** and create a case with a legit name (e.g. `Ongole Tobacco Smuggling Syndicate`).
3. Click **Upload Records** for each suspect:
   * Select a Suspect Name (e.g., `Kalyan Chakravarthy`).
   * Select and drag the CDR file (`Case1_Ongole_Tobacco_Smuggling_CDR_Kalyan_Chakravarthy.csv`).
   * Select and drag the corresponding IPDR file (`Case1_Ongole_Tobacco_Smuggling_IPDR_Kalyan_Chakravarthy.csv`).
   * Click **Upload**.
4. Repeat for other suspects in the case.
5. In the case page, click **Run Analysis** to execute the analytics engines. TRACE will automatically display the resolved network graph, tower mapping coordinates, and highlight all detected intelligence events!
