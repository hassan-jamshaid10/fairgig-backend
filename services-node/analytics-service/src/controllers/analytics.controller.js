const { pool } = require('../db/pool');

// ============================================
// Endpoint 1: GET /analytics/city-median
// ============================================
const getCityMedian = async (req, res) => {
  const { city_zone } = req.query;

  if (!city_zone) {
    return res.status(400).json({ 
      detail: "city_zone query parameter is required" 
    });
  }

  try {
    const query = `
      SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (
          ORDER BY s.net_received / NULLIF(s.hours_worked, 0)
        ) AS median_hourly_rate,
        COUNT(DISTINCT s.worker_id) AS sample_size
      FROM earnings_svc.shifts s
      JOIN auth_svc.users u ON u.id = s.worker_id
      WHERE u.city_zone = $1
        AND s.shift_date > NOW() - INTERVAL '60 days'
    `;

    const result = await pool.query(query, [city_zone]);
    const row = result.rows[0];
    const sampleSize = parseInt(row.sample_size) || 0;

    // Privacy rule: return null if sample too small
    if (sampleSize < 5) {
      return res.json({
        data: {
          city_zone,
          median_hourly_rate: null,
          sample_size: sampleSize,
          period: "last 60 days",
          note: "Not enough data in this zone for a reliable median"
        }
      });
    }

    res.json({
      data: {
        city_zone,
        median_hourly_rate: parseFloat(row.median_hourly_rate).toFixed(2),
        sample_size: sampleSize,
        period: "last 60 days"
      }
    });
  } catch (error) {
    console.error('[city-median] error:', error.message);
    res.status(500).json({ detail: "Failed to compute city median" });
  }
};

// ============================================
// Endpoint 2: GET /analytics/commission-trends
// ============================================
const getCommissionTrends = async (req, res) => {
  const { platform } = req.query;
  let days = parseInt(req.query.days) || 30;

  if (!platform) {
    return res.status(400).json({ 
      detail: "platform query parameter is required" 
    });
  }

  // Cap days at 90 to prevent expensive queries
  if (days > 90) days = 90;
  if (days < 1) days = 30;

  try {
    const query = `
      SELECT
        shift_date,
        AVG(
          platform_deductions / NULLIF(gross_earned, 0) * 100
        ) AS avg_commission_rate,
        COUNT(*) AS shift_count
      FROM earnings_svc.shifts
      WHERE platform = $1
        AND shift_date > NOW() - ($2 || ' days')::INTERVAL
      GROUP BY shift_date
      ORDER BY shift_date ASC
    `;

    const result = await pool.query(query, [platform, days]);

    const trend = result.rows.map(row => ({
      date: row.shift_date,
      avg_commission_rate: parseFloat(row.avg_commission_rate).toFixed(2),
      shift_count: parseInt(row.shift_count)
    }));

    res.json({
      data: {
        platform,
        period_days: days,
        trend
      }
    });
  } catch (error) {
    console.error('[commission-trends] error:', error.message);
    res.status(500).json({ detail: "Failed to compute commission trends" });
  }
};

// ============================================
// Endpoint 3: GET /analytics/zone-distribution
// ============================================
const getZoneDistribution = async (req, res) => {
  // Role check: Advocate only
  if (req.user.role !== 'Advocate') {
    return res.status(403).json({ 
      detail: "Only advocates can access zone distribution" 
    });
  }

  let days = parseInt(req.query.days) || 30;
  if (days > 365) days = 365;
  if (days < 1) days = 30;

  try {
    const query = `
      SELECT
        u.city_zone,
        AVG(s.net_received / NULLIF(s.hours_worked, 0)) AS avg_hourly_rate,
        AVG(s.net_received) AS avg_shift_income,
        COUNT(DISTINCT s.worker_id) AS worker_count,
        COUNT(*) AS shift_count
      FROM earnings_svc.shifts s
      JOIN auth_svc.users u ON u.id = s.worker_id
      WHERE s.shift_date > NOW() - ($1 || ' days')::INTERVAL
        AND u.city_zone IS NOT NULL
      GROUP BY u.city_zone
      HAVING COUNT(DISTINCT s.worker_id) >= 3
      ORDER BY avg_hourly_rate ASC
    `;

    const result = await pool.query(query, [days]);

    const data = result.rows.map(row => ({
      city_zone: row.city_zone,
      avg_hourly_rate: parseFloat(row.avg_hourly_rate).toFixed(2),
      avg_shift_income: parseFloat(row.avg_shift_income).toFixed(2),
      worker_count: parseInt(row.worker_count),
      shift_count: parseInt(row.shift_count)
    }));

    res.json({ 
      data,
      period_days: days
    });
  } catch (error) {
    console.error('[zone-distribution] error:', error.message);
    res.status(500).json({ detail: "Failed to compute zone distribution" });
  }
};

// ============================================
// Endpoint 4: GET /analytics/vulnerability-flags
// ============================================
const getVulnerabilityFlags = async (req, res) => {
  // Role check: Advocate only
  if (req.user.role !== 'Advocate') {
    return res.status(403).json({ 
      detail: "Only advocates can access vulnerability flags" 
    });
  }

  try {
    const query = `
      WITH prev_month AS (
        SELECT
          worker_id,
          SUM(net_received) AS total
        FROM earnings_svc.shifts
        WHERE shift_date >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')
          AND shift_date < DATE_TRUNC('month', NOW())
        GROUP BY worker_id
      ),
      curr_month AS (
        SELECT
          worker_id,
          SUM(net_received) AS total
        FROM earnings_svc.shifts
        WHERE shift_date >= DATE_TRUNC('month', NOW())
        GROUP BY worker_id
      )
      SELECT
        MD5(p.worker_id::text) AS pseudo_id,
        u.city_zone,
        p.total AS previous_month_total,
        COALESCE(c.total, 0) AS current_month_total,
        ROUND(
          ((p.total - COALESCE(c.total, 0)) / NULLIF(p.total, 0) * 100)::numeric, 
          1
        ) AS drop_percentage
      FROM prev_month p
      LEFT JOIN curr_month c ON c.worker_id = p.worker_id
      JOIN auth_svc.users u ON u.id = p.worker_id
      WHERE p.total > 0
        AND ((p.total - COALESCE(c.total, 0)) / p.total * 100) > 20
      ORDER BY drop_percentage DESC
    `;

    const result = await pool.query(query);

    const data = result.rows.map(row => ({
      pseudo_id: row.pseudo_id,
      city_zone: row.city_zone,
      previous_month_total: parseFloat(row.previous_month_total).toFixed(2),
      current_month_total: parseFloat(row.current_month_total).toFixed(2),
      drop_percentage: parseFloat(row.drop_percentage)
    }));

    res.json({ 
      data,
      total_flagged: data.length
    });
  } catch (error) {
    console.error('[vulnerability-flags] error:', error.message);
    res.status(500).json({ detail: "Failed to compute vulnerability flags" });
  }
};

// ============================================
// Endpoint 5: GET /analytics/top-complaints
// ============================================
const getTopComplaints = async (req, res) => {
  // Role check: Advocate only
  if (req.user.role !== 'Advocate') {
    return res.status(403).json({ 
      detail: "Only advocates can access top complaints" 
    });
  }

  let days = parseInt(req.query.days) || 7;
  if (days > 90) days = 90;
  if (days < 1) days = 7;

  try {
    const query = `
      SELECT
        category,
        platform,
        COUNT(*) AS complaint_count
      FROM grievance_svc.grievances
      WHERE created_at > NOW() - ($1 || ' days')::INTERVAL
      GROUP BY category, platform
      ORDER BY complaint_count DESC
      LIMIT 10
    `;

    const result = await pool.query(query, [days]);

    const data = result.rows.map(row => ({
      category: row.category,
      platform: row.platform,
      complaint_count: parseInt(row.complaint_count)
    }));

    res.json({ 
      data,
      period_days: days
    });
  } catch (error) {
    console.error('[top-complaints] error:', error.message);
    res.status(500).json({ detail: "Failed to fetch top complaints" });
  }
};

// ============================================
// Endpoint 6: GET /analytics/platforms
// ============================================
const getPlatforms = async (req, res) => {
  try {
    const query = `
      SELECT DISTINCT platform
      FROM earnings_svc.shifts
      WHERE platform IS NOT NULL
      ORDER BY platform ASC
    `;

    const result = await pool.query(query);
    const data = result.rows.map(row => row.platform);

    res.json({ data });
  } catch (error) {
    console.error('[platforms] error:', error.message);
    res.status(500).json({ detail: "Failed to fetch platforms" });
  }
};

module.exports = {
  getCityMedian,
  getCommissionTrends,
  getZoneDistribution,
  getVulnerabilityFlags,
  getTopComplaints,
  getPlatforms
};