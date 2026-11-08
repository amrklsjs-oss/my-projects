const readBooks = require("./read-books");
const saveBooks = require("./save-books");

async function updateBook(id, title) {
  if (!title) {
    console.log("invalid title");
    return;
  }
  try {
    const books = await readBooks();
    let book = books.find((b) => b.id == id);
    if (!book) {
      console.log("book not found");
      return;
    }
    book.title = title;
    await saveBooks(books);
  } catch (err) {
    console.log(err);
  }
}

module.exports = updateBook;