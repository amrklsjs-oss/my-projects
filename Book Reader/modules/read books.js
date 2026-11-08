const { readFile } = require("fs").promises;
const path = require("path");

const filePath = path.join(__dirname, "../data/read books.json");

async function readBooks() {
    try {
        const data = await readFile(filePath, "utf-8");
        const books = JSON.parse(data);
        return books;
    } catch (error) {
        console.log(error);
    }
}

module.exports = readBooks;