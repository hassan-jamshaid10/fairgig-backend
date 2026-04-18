const { pool } = require('../db/pool');
const { v4: uuidv4 } = require('uuid');

// INTERNAL HELPER: Data Aggregator (Feature 1)
const generateCertificateData = async (workerId, startDate, endDate) => {
  // STEP 1: Get the worker
  const workerQuery = `SELECT id, full_name, phone, city_zone FROM auth_svc.user_with_role WHERE id = $1`;
  const workerResult = await pool.query(workerQuery, [workerId]);
  
  if (workerResult.rows.length === 0) {
    const error = new Error("Worker not found in auth_svc");
    error.status = 404;
    throw error;
  }
  
  const worker = workerResult.rows[0];

  // STEP 2: Get all shifts and cross-reference screenshots
  const shiftsQuery = `
    SELECT 
      s.id, s.platform, s.shift_date, 
      s.hours_worked, s.gross_earned, 
      s.platform_deductions, s.net_received,
      sc.status as screenshot_status
    FROM earnings_svc.shifts s
    LEFT JOIN earnings_svc.screenshots sc ON sc.shift_id = s.id
    WHERE s.worker_id = $1 AND s.shift_date >= $2 AND s.shift_date <= $3
    ORDER BY s.shift_date ASC
  `;
  const shiftsResult = await pool.query(shiftsQuery, [workerId, startDate, endDate]);
  const rows = shiftsResult.rows;

  // STEP 3: Crunch the numbers
  let totals = { gross: 0, deductions: 0, net: 0, shifts_count: rows.length, hours_total: 0 };
  let platformMap = {};
  let monthlyMap = {};
  let verifSummary = {
    total_shifts: rows.length, verified_shifts: 0, pending_shifts: 0, 
    flagged_shifts: 0, unverifiable_shifts: 0, no_screenshot_shifts: 0
  };

  rows.forEach(row => {
    const gross = parseFloat(row.gross_earned) || 0;
    const deductions = parseFloat(row.platform_deductions) || 0;
    const net = parseFloat(row.net_received) || 0;
    const hours = parseFloat(row.hours_worked) || 0;

    totals.gross += gross; totals.deductions += deductions;
    totals.net += net; totals.hours_total += hours;

    if (!platformMap[row.platform]) {
      platformMap[row.platform] = { platform: row.platform, shifts_count: 0, gross: 0, deductions: 0, net: 0, verified_count: 0 };
    }
    const pData = platformMap[row.platform];
    pData.shifts_count++; pData.gross += gross; pData.deductions += deductions; pData.net += net;

    const status = row.screenshot_status;
    if (status === 'Confirmed') { verifSummary.verified_shifts++; pData.verified_count++; }
    else if (status === 'Pending') verifSummary.pending_shifts++;
    else if (status === 'Flagged') verifSummary.flagged_shifts++;
    else if (status === 'Unverifiable') verifSummary.unverifiable_shifts++;
    else verifSummary.no_screenshot_shifts++;

    const d = new Date(row.shift_date);
    const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    if (!monthlyMap[monthStr]) monthlyMap[monthStr] = { month: monthStr, net_total: 0 };
    monthlyMap[monthStr].net_total += net;
  });

  const per_platform = Object.values(platformMap).map(p => ({
    ...p, verification_pct: p.shifts_count > 0 ? parseFloat(((p.verified_count / p.shifts_count) * 100).toFixed(1)) : 0
  }));
  const monthly_breakdown = Object.values(monthlyMap).sort((a, b) => a.month.localeCompare(b.month));

  // STEP 4: Generate Metadata
  const certificateId = `FG-${uuidv4().substring(0, 8).toUpperCase()}`;
  return {
    worker,
    period: { from: startDate, to: endDate, formatted: `${startDate} to ${endDate}` },
    totals, per_platform, monthly_breakdown,
    verification_summary: verifSummary,
    certificate_id: certificateId,
    generated_at: new Date().toISOString()
  };
};

// FEATURE 2: GET /certificates/me
const getWorkerCertificateData = async (req, res) => {
  const workerId = req.user.sub;
  const userRole = req.user.role;

  // 1. Role Security Check
  if (!userRole || userRole.toLowerCase() !== 'worker') {
    return res.status(403).json({ detail: "Only workers can generate their own certificates" });
  }

  // 2. Date Parsing and Defaults
  let startDateStr = req.query.from;
  let endDateStr = req.query.to;

  const formatDate = (date) => date.toISOString().split('T')[0]; // Format as YYYY-MM-DD

  // If 'to' is missing, default to today
  if (!endDateStr) {
    endDateStr = formatDate(new Date());
  }
  
  // If 'from' is missing, default to 90 days before 'to' date
  if (!startDateStr) {
    const endDateObj = new Date(endDateStr);
    endDateObj.setDate(endDateObj.getDate() - 90);
    startDateStr = formatDate(endDateObj);
  }

  // 3. Date Validation Rule
  if (new Date(startDateStr) > new Date(endDateStr)) {
    return res.status(400).json({ detail: "from date must be before to date" });
  }

  // 4. Call the Aggregator
  try {
    const certificateData = await generateCertificateData(workerId, startDateStr, endDateStr);
    
    // 5. Return the JSON
    res.status(200).json(certificateData);
  } catch (error) {
    if (error.status === 404) {
      return res.status(404).json({ detail: error.message });
    }
    console.error("Certificate Data Error:", error);
    res.status(500).json({ detail: "Failed to generate certificate data" });
  }
};


const getWorkerCertificateById = async (req, res) => {
  const targetWorkerId = req.params.worker_id;
  const callerId = req.user.sub;
  const callerRole = req.user.role ? req.user.role.toLowerCase() : 'worker';

  // 1. Access Control Logic
  if (callerRole === 'worker' && callerId !== targetWorkerId) {
    return res.status(403).json({ detail: "Workers can only view their own certificates" });
  }
  // Advocates and Verifiers pass through naturally.

  // 2. Date Parsing and Defaults (Same logic as Feature 2)
  let startDateStr = req.query.from;
  let endDateStr = req.query.to;

  const formatDate = (date) => date.toISOString().split('T')[0];

  if (!endDateStr) {
    endDateStr = formatDate(new Date());
  }
  if (!startDateStr) {
    const endDateObj = new Date(endDateStr);
    endDateObj.setDate(endDateObj.getDate() - 90);
    startDateStr = formatDate(endDateObj);
  }

  if (new Date(startDateStr) > new Date(endDateStr)) {
    return res.status(400).json({ detail: "from date must be before to date" });
  }

  // 3. Call the Aggregator
  try {
    const certificateData = await generateCertificateData(targetWorkerId, startDateStr, endDateStr);
    res.status(200).json(certificateData);
  } catch (error) {
    if (error.status === 404) {
      return res.status(404).json({ detail: "Worker not found or no data available" });
    }
    console.error("Certificate Data Error:", error);
    res.status(500).json({ detail: "Failed to fetch certificate data" });
  }
};

// Update your exports at the very bottom
module.exports = {
  generateCertificateData,
  previewCertificateData, 
  getWorkerCertificateData,
  getWorkerCertificateById
};