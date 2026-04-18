require('dotenv').config();
const app = require('./src/app');

const PORT = process.env.PORT || 8004;

app.listen(PORT, () => {
  console.log(`Grievance Service is running on port ${PORT}`);
});