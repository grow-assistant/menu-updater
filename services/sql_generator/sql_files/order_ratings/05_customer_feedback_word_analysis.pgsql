-- Customer feedback word analysis (feedback_word_analysis)
-- Extract and analyze common words from customer feedback comments

WITH feedback_words AS (
    -- Extract individual words from feedback
    SELECT
        r.id AS rating_id,
        i.id AS item_id,
        i.name AS item_name,
        c.name AS category,
        orf.value AS rating,
        orf.notes AS comment,
        TRIM(LOWER(word)) AS word
    FROM
        order_ratings r
    JOIN
        orders o ON r.order_id = o.id
    JOIN
        order_items oi ON o.id = oi.order_id
    JOIN
        items i ON oi.item_id = i.id
    JOIN
        categories c ON i.category_id = c.id
    JOIN
        menus m ON c.menu_id = m.id
    JOIN
        order_ratings_feedback orf ON r.id = orf.rating_id,
        LATERAL UNNEST(STRING_TO_ARRAY(LOWER(orf.notes), ' ')) AS word
    WHERE
        m.location_id = 62
        AND r.created_at >= CURRENT_DATE - INTERVAL '90 days'
        AND LENGTH(orf.notes) > 5
        AND o.status = 7
),
word_counts AS (
    -- Count frequency of each word by rating level
    SELECT
        word,
        COUNT(*) AS total_occurrences,
        COUNT(DISTINCT rating_id) AS appears_in_n_comments,
        COUNT(CASE WHEN rating >= 4 THEN 1 END) AS positive_rating_count,
        COUNT(CASE WHEN rating <= 2 THEN 1 END) AS negative_rating_count,
        ROUND(AVG(rating), 2) AS avg_rating_with_word
    FROM
        feedback_words
    WHERE
        LENGTH(word) > 3
        AND word NOT IN (
            'this', 'that', 'there', 'these', 'those', 'from', 'have', 'with',
            'they', 'would', 'could', 'should', 'were', 'their', 'when', 'what',
            'your', 'will', 'about', 'just', 'very', 'much', 'more', 'some', 'been'
        )
    GROUP BY
        word
    HAVING
        COUNT(*) >= 5
),
sentiment_words AS (
    -- Categorize words by sentiment (positive vs negative)
    SELECT
        word,
        total_occurrences,
        appears_in_n_comments,
        positive_rating_count,
        negative_rating_count,
        avg_rating_with_word,
        ROUND(positive_rating_count::numeric / NULLIF(positive_rating_count + negative_rating_count, 0) * 100, 1) AS positivity_score,
        CASE
            WHEN positive_rating_count > negative_rating_count * 3 THEN 'Positive'
            WHEN negative_rating_count > positive_rating_count * 2 THEN 'Negative'
            ELSE 'Neutral'
        END AS sentiment
    FROM
        word_counts
),
word_item_counts AS (
    -- Precompute the counts of items associated with each word
    SELECT 
        fw.word,
        fw.item_name,
        COUNT(*) AS item_count
    FROM 
        feedback_words fw
    GROUP BY 
        fw.word, fw.item_name
)
-- Final analysis
SELECT
    sw.word,
    sw.total_occurrences,
    sw.appears_in_n_comments,
    sw.avg_rating_with_word,
    sw.positivity_score,
    sw.sentiment,
    -- Top menu items associated with this word
    (SELECT STRING_AGG(item_name, ', ')
     FROM (
         SELECT item_name
         FROM word_item_counts wic
         WHERE wic.word = sw.word
         ORDER BY wic.item_count DESC
         LIMIT 3
     ) top_items
    ) AS top_associated_items
FROM
    sentiment_words sw
ORDER BY
    CASE sw.sentiment
        WHEN 'Negative' THEN 1
        WHEN 'Neutral' THEN 2
        WHEN 'Positive' THEN 3
    END,
    sw.total_occurrences DESC; 