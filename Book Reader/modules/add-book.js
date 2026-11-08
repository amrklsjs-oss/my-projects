const readBooks = require("./read-books");
const saveBooks = require("./save-books");

async function addBook(title, author, year) {
  if (!title || !author || !year) {
    console.log("Invalid data");
    return;
  }

  try {
    let books = await readBooks();
    let book = { id: books[books.length - 1].id + 1, title, author, year };
    books.push(book);
    await saveBooks(books);
  } catch (error) {
    console.log(error);
  }
}

module.exports = addBook;