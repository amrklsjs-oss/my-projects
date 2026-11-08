const { writeFile } = require("fs").promises;
const path = require("path");

const filePath = path.join(__dirname, "../data/save books.json");

async function saveBooks(books) {
    try {
        await writeFile(filePath, JSON.stringify(books, null, 2));
    } catch (error) {
        console.log(error);
    }
}

module.exports = saveBooks;