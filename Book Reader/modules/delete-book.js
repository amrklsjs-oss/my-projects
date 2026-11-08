const readBooks = require("./read-books");
const saveBooks = require("./save-books");

async function deleteBook(id) {
  try {
    let books = await readBooks();

    let index = books.findIndex((b) => b.id == id);

    if (index == -1) {
      console.log("book not found");
      return;
    }

    books.splice(index, 1);
    await saveBooks(books);
  } catch (err) {
    console.log(err);
  }
}

module.exports = deleteBook;