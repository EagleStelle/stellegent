UPDATE lectures
SET visibility = 'private'
WHERE visibility <> 'private'
  AND course_id IN (
      SELECT id
      FROM courses
      WHERE visibility = 'private'
  );
