const pool = require('../db/pool');
const stringSimilarity = require('string-similarity');
const { v4: uuidv4 } = require('uuid');

// FEATURE 1: Create a Grievance
const createGrievance = async (req, res) => {
  const { platform, category, description, is_anonymous, tags } = req.body;
  const worker_id = req.user.sub;
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    const grievanceQuery = `
      INSERT INTO grievance_svc.grievances 
      (worker_id, platform, category, description, status, is_anonymous, created_at)
      VALUES ($1, $2, $3, $4, 'Open', $5, NOW())
      RETURNING id, platform, category, description, status, is_anonymous, created_at;
    `;
    const grievanceValues = [worker_id, platform, category, description, is_anonymous];
    const grievanceResult = await client.query(grievanceQuery, grievanceValues);
    const newGrievance = grievanceResult.rows[0];

    if (tags && Array.isArray(tags) && tags.length > 0) {
      const tagQueries = tags.map(tag => {
        return client.query(
          `INSERT INTO grievance_svc.grievance_tags (grievance_id, tag_name, created_at) 
           VALUES ($1, $2, NOW())`,
          [newGrievance.id, tag]
        );
      });
      await Promise.all(tagQueries);
    }

    await client.query('COMMIT');

    if (newGrievance.is_anonymous) {
      delete newGrievance.worker_id;
    }
    
    newGrievance.tags = tags || [];
    res.status(201).json(newGrievance);

  } catch (error) {
    await client.query('ROLLBACK');
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to save grievance and tags" });
  } finally {
    client.release();
  }
};

// FEATURE 2: Get List of Grievances (With Paging & Filters)
const getGrievances = async (req, res) => {
  try {
    const platform = req.query.platform || null;
    const category = req.query.category || null;
    const status = req.query.status || null;
    const limit = parseInt(req.query.limit) || 50;
    const offset = parseInt(req.query.offset) || 0;

    const query = `
      SELECT 
        g.id, 
        CASE WHEN g.is_anonymous THEN NULL ELSE g.worker_id END as worker_id,
        g.platform, 
        g.category, 
        CASE 
          WHEN LENGTH(g.description) > 300 THEN SUBSTRING(g.description, 1, 300) || '...' 
          ELSE g.description 
        END AS description, 
        g.status, 
        g.is_anonymous, 
        g.created_at,
        g.cluster_id, -- FIXED: Using the actual column now
        
        COALESCE(
          (SELECT json_agg(tag_name) FROM grievance_svc.grievance_tags WHERE grievance_id = g.id), 
          '[]'
        ) AS tags,
        
        (SELECT COUNT(*)::int FROM grievance_svc.grievance_comments WHERE grievance_id = g.id) AS comment_count

      FROM grievance_svc.grievances g
      WHERE ($1::text IS NULL OR g.platform = $1)
        AND ($2::text IS NULL OR g.category = $2)
        AND ($3::text IS NULL OR g.status = $3)
      
      ORDER BY g.created_at DESC
      LIMIT $4 OFFSET $5;
    `;

    const values = [platform, category, status, limit, offset];
    const result = await pool.query(query, values);

    res.status(200).json(result.rows);

  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to fetch grievances" });
  }
};

// FEATURE 3: Get Full Details of One Grievance
const getGrievanceById = async (req, res) => {
  const { id } = req.params;

  try {
    const query = `
      WITH cluster_data AS (
        SELECT 
          cluster_id,
          platform,
          category,
          COUNT(*) OVER (PARTITION BY cluster_id) as cluster_size
        FROM grievance_svc.grievances
        WHERE cluster_id IS NOT NULL
      )
      SELECT 
        g.id, 
        CASE WHEN g.is_anonymous THEN NULL ELSE g.worker_id END as worker_id,
        g.platform, 
        g.category, 
        g.description, 
        g.status, 
        g.is_anonymous, 
        g.created_at,
        g.cluster_id,

        COALESCE(
          (SELECT json_agg(json_build_object('tag_name', tag_name, 'created_at', created_at)) 
           FROM grievance_svc.grievance_tags WHERE grievance_id = g.id), 
          '[]'
        ) AS tags,

        COALESCE(
          (SELECT json_agg(c) FROM (
             SELECT * FROM grievance_svc.grievance_comments 
             WHERE grievance_id = g.id 
             ORDER BY created_at ASC 
             LIMIT 20
          ) c), 
          '[]'
        ) AS comments,

        (SELECT COUNT(*)::int FROM grievance_svc.grievance_comments WHERE grievance_id = g.id) AS comment_count,

        CASE 
          WHEN g.cluster_id IS NOT NULL THEN 
            (SELECT json_build_object(
              'total_in_cluster', cd.cluster_size,
              'platform', cd.platform,
              'category', cd.category
            ) FROM cluster_data cd WHERE cd.cluster_id = g.cluster_id LIMIT 1)
          ELSE NULL 
        END AS cluster_info

      FROM grievance_svc.grievances g
      WHERE g.id = $1;
    `;

    const result = await pool.query(query, [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ detail: "Grievance not found" });
    }

    res.status(200).json(result.rows[0]);

  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to fetch grievance details" });
  }
};

// FEATURE 3.1: Load More Comments
const getCommentsByGrievanceId = async (req, res) => {
  const { id } = req.params;
  const limit = parseInt(req.query.limit) || 20;
  const offset = parseInt(req.query.offset) || 0;

  try {
    const query = `
      SELECT * FROM grievance_svc.grievance_comments
      WHERE grievance_id = $1
      ORDER BY created_at ASC
      LIMIT $2 OFFSET $3;
    `;

    const result = await pool.query(query, [id, limit, offset]);

    res.status(200).json({
      grievance_id: id,
      limit,
      offset,
      comments: result.rows
    });

  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to fetch comments" });
  }
};

// FEATURE 4: Add a Comment
const addComment = async (req, res) => {
  const { id: grievance_id } = req.params;
  const { comment_text } = req.body;
  const worker_id = req.user.sub;

  try {
    const grievanceCheck = await pool.query(
      'SELECT worker_id, is_anonymous FROM grievance_svc.grievances WHERE id = $1',
      [grievance_id]
    );

    if (grievanceCheck.rows.length === 0) {
      return res.status(404).json({ detail: "Grievance not found" });
    }

    const originalGrievance = grievanceCheck.rows[0];

    const insertQuery = `
      INSERT INTO grievance_svc.grievance_comments (grievance_id, worker_id, comment_text, created_at)
      VALUES ($1, $2, $3, NOW())
      RETURNING *;
    `;
    const result = await pool.query(insertQuery, [grievance_id, worker_id, comment_text]);
    const newComment = result.rows[0];

    let displayName = "Worker " + worker_id.substring(0, 5);
    
    if (originalGrievance.is_anonymous && originalGrievance.worker_id === worker_id) {
      displayName = "Anonymous (Author)";
      newComment.worker_id = null;
    }

    res.status(201).json({
      ...newComment,
      display_name: displayName
    });

  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to post comment" });
  }
};

// FEATURE 6: Add Advocate Tag (Priority)
const addAdvocateTag = async (req, res) => {
  const { id: grievance_id } = req.params;
  const { tag_name } = req.body;
  const { role } = req.user; 

  // FIXED: Case-insensitive check for "Advocate"
  if (!role || role.toLowerCase() !== 'advocate') {
    return res.status(403).json({ detail: "Only advocates can prioritize tags" });
  }

  try {
    const checkQuery = `
      SELECT id FROM grievance_svc.grievance_tags 
      WHERE grievance_id = $1 AND tag_name = $2
    `;
    const checkResult = await pool.query(checkQuery, [grievance_id, tag_name]);

    if (checkResult.rows.length > 0) {
      return res.status(400).json({ detail: "This tag is already attached to this grievance" });
    }

    const insertQuery = `
      INSERT INTO grievance_svc.grievance_tags (grievance_id, tag_name, is_advocate_tag, created_at)
      VALUES ($1, $2, TRUE, NOW())
    `;
    await pool.query(insertQuery, [grievance_id, tag_name]);

    const refreshQuery = `
      SELECT tag_name, is_advocate_tag, created_at 
      FROM grievance_svc.grievance_tags 
      WHERE grievance_id = $1
      ORDER BY is_advocate_tag DESC, created_at DESC
    `;
    const finalTags = await pool.query(refreshQuery, [grievance_id]);

    res.status(200).json(finalTags.rows);

  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to add advocate tag" });
  }
};

const getTrendingTags = async (req, res) => {
  try {
    const query = `
      SELECT 
        tag_name,
        -- Count how many times advocates used this tag
        COUNT(*) FILTER (WHERE is_advocate_tag = TRUE)::int as advocate_mentions,
        -- Count how many times workers used this tag
        COUNT(*) FILTER (WHERE is_advocate_tag = FALSE)::int as worker_mentions,
        -- Calculate the Trend Score (Advocate = 10 points, Worker = 1 point)
        (COUNT(*) FILTER (WHERE is_advocate_tag = TRUE) * 10 + 
         COUNT(*) FILTER (WHERE is_advocate_tag = FALSE))::int as trend_score
      FROM grievance_svc.grievance_tags
      GROUP BY tag_name
      ORDER BY trend_score DESC
      LIMIT 10; -- Show top 10 trends
    `;

    const result = await pool.query(query);

    res.status(200).json(result.rows);
  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to fetch trending tags" });
  }
};

const clusterGrievances = async (req, res) => {
  const { role } = req.user;

  // Security: Advocate only
  if (!role || role.toLowerCase() !== 'advocate') {
    return res.status(403).json({ detail: "Only advocates can trigger auto-clustering" });
  }

  const client = await pool.connect();
  try {
    // 1. Fetch all Open grievances that don't have a cluster yet
    const fetchQuery = `
      SELECT id, platform, category, description 
      FROM grievance_svc.grievances 
      WHERE status = 'Open' AND cluster_id IS NULL;
    `;
    const candidates = await pool.query(fetchQuery);

    if (candidates.rows.length === 0) {
      return res.status(200).json({ clusters_created: 0, grievances_updated: 0 });
    }

    // 2. Group by Platform + Category
    const groups = {};
    candidates.rows.forEach(g => {
      const key = `${g.platform}-${g.category}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(g);
    });

    let clustersCreated = 0;
    let totalUpdated = 0;

    await client.query('BEGIN');

    // 3. Process each group
    for (const key in groups) {
      const items = groups[key];
      const processedIds = new Set();

      for (let i = 0; i < items.length; i++) {
        if (processedIds.has(items[i].id)) continue;

        const currentCluster = [items[i]];
        
        for (let j = i + 1; j < items.length; j++) {
          if (processedIds.has(items[j].id)) continue;

          // Compare text using Dice's Coefficient (Library)
          const similarity = stringSimilarity.compareTwoStrings(
            items[i].description, 
            items[j].description
          );

          // Threshold check: 0.35 (35% similar)
          if (similarity > 0.35) {
            currentCluster.push(items[j]);
          }
        }

        // 4. Strength Rule: Only cluster if 3 or more members
        if (currentCluster.length >= 3) {
          const newClusterId = uuidv4();
          const idsToUpdate = currentCluster.map(c => c.id);
          
          await client.query(
            'UPDATE grievance_svc.grievances SET cluster_id = $1 WHERE id = ANY($2)',
            [newClusterId, idsToUpdate]
          );

          idsToUpdate.forEach(id => processedIds.add(id));
          clustersCreated++;
          totalUpdated += idsToUpdate.length;
        }
      }
    }

    await client.query('COMMIT');
    res.status(200).json({ clusters_created: clustersCreated, grievances_updated: totalUpdated });

  } catch (error) {
    await client.query('ROLLBACK');
    console.error("Clustering Error:", error);
    res.status(500).json({ detail: "Clustering process failed" });
  } finally {
    client.release();
  }
};

const getClusterSummaries = async (req, res) => {
  try {
    const query = `
      SELECT 
        cluster_id,
        platform,
        category,
        COUNT(*)::int as member_count,
        -- Find the date range of the issue
        MIN(created_at) as first_reported,
        MAX(created_at) as last_reported,
        -- Subquery to grab a single sample description for the preview
        (SELECT description FROM grievance_svc.grievances 
         WHERE cluster_id = g.cluster_id LIMIT 1) as sample_description,
        -- Collect unique tags from ALL grievances in this cluster
        COALESCE(
          (SELECT json_agg(DISTINCT tag_name) 
           FROM grievance_svc.grievance_tags 
           WHERE grievance_id IN (
             SELECT id FROM grievance_svc.grievances WHERE cluster_id = g.cluster_id
           )), 
          '[]'
        ) AS tags
      FROM grievance_svc.grievances g
      WHERE cluster_id IS NOT NULL
      GROUP BY cluster_id, platform, category
      HAVING COUNT(*) >= 3 -- Rule: Only 3 or more members
      ORDER BY member_count DESC; -- Priority: Biggest clusters first
    `;

    const result = await pool.query(query);

    res.status(200).json(result.rows);
  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to fetch cluster summaries" });
  }
};

const getTrendingTagsVolume = async (req, res) => {
  // 1. Get days from query, default to 7
  const days = parseInt(req.query.days) || 7;

  try {
    // 2. Count tags within the time window
    const query = `
      SELECT tag_name, COUNT(*)::int as count
      FROM grievance_svc.grievance_tags
      WHERE created_at > NOW() - ($1 || ' days')::INTERVAL
      GROUP BY tag_name
      ORDER BY count DESC
      LIMIT 10;
    `;

    const result = await pool.query(query, [days]);

    // 3. Match the exact response format required
    res.status(200).json({
      trending: result.rows,
      period_days: days
    });
  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to fetch volume-based trends" });
  }
};

// Add getTrendingTagsVolume to your exports

// Update your exports to include getTrendingTags
module.exports = { 
  createGrievance, 
  getGrievances, 
  getGrievanceById, 
  getCommentsByGrievanceId,
  addComment,
  addAdvocateTag,
  getTrendingTags,
  clusterGrievances,
  getClusterSummaries,
  getTrendingTagsVolume // <--- MAKE SURE THIS IS HERE
};