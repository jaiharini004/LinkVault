// ==========================================
// LINKVAULT - SMART LINK ORGANIZER
// Frontend JavaScript
// ==========================================


// ------------------------------------------
// Data
// ------------------------------------------

let links = [

    {
        id: 1,
        title: "Google",
        url: "https://www.google.com",
        category: "Search",
        description: "Google search engine",
        favorite: false
    },

    {
        id: 2,
        title: "GitHub",
        url: "https://github.com",
        category: "Development",
        description: "Platform for developers and repositories",
        favorite: true
    },

    {
        id: 3,
        title: "YouTube",
        url: "https://www.youtube.com",
        category: "Entertainment",
        description: "Video sharing platform",
        favorite: false
    }

];


// ------------------------------------------
// Variables
// ------------------------------------------

let editingLinkId = null;


// ------------------------------------------
// Get HTML Elements
// ------------------------------------------

const titleInput = document.getElementById("titleInput");
const urlInput = document.getElementById("urlInput");
const categoryInput = document.getElementById("categoryInput");
const descriptionInput = document.getElementById("descriptionInput");

const addLinkBtn = document.getElementById("addLinkBtn");

const linksContainer = document.getElementById("linksContainer");

const searchInput = document.getElementById("searchInput");


// Modal elements

const editModal = document.getElementById("editModal");

const closeModalBtn = document.getElementById("closeModalBtn");

const editTitle = document.getElementById("editTitle");
const editUrl = document.getElementById("editUrl");
const editCategory = document.getElementById("editCategory");
const editDescription = document.getElementById("editDescription");

const saveEditBtn = document.getElementById("saveEditBtn");


// ------------------------------------------
// Render Links
// ------------------------------------------

function renderLinks(filteredLinks = links) {

    linksContainer.innerHTML = "";

    if (filteredLinks.length === 0) {

        linksContainer.innerHTML = `
            <div class="empty-message">
                <h3>No links found 😔</h3>
                <p>Try adding a new link or change your search.</p>
            </div>
        `;

        return;
    }


    filteredLinks.forEach(function(link) {

        const card = document.createElement("div");

        card.className = "link-card";


        card.innerHTML = `

            <h3>${escapeHTML(link.title)}</h3>

            <span class="category">
                ${escapeHTML(link.category || "General")}
            </span>

            <p class="description">
                ${escapeHTML(link.description || "No description")}
            </p>

            <a
                class="link-url"
                href="${escapeAttribute(link.url)}"
                target="_blank"
            >
                ${escapeHTML(link.url)}
            </a>

            <div class="buttons">

                <button
                    class="open-btn"
                    onclick="openLink('${escapeAttribute(link.url)}')"
                >
                    🔗 Open
                </button>

                <button
                    class="edit-btn"
                    onclick="openEditModal(${link.id})"
                >
                    ✏️ Edit
                </button>

                <button
                    class="delete-btn"
                    onclick="deleteLink(${link.id})"
                >
                    🗑️ Delete
                </button>

                <button
                    class="favorite-btn"
                    onclick="toggleFavorite(${link.id})"
                >
                    ${link.favorite ? "❤️ Favorited" : "🤍 Favorite"}
                </button>

            </div>
        `;


        linksContainer.appendChild(card);

    });

}


// ------------------------------------------
// Add Link
// ------------------------------------------

addLinkBtn.addEventListener("click", function() {

    const title = titleInput.value.trim();
    const url = urlInput.value.trim();
    const category = categoryInput.value.trim();
    const description = descriptionInput.value.trim();


    // Validation

    if (title === "") {

        alert("Please enter a title.");

        titleInput.focus();

        return;
    }


    if (url === "") {

        alert("Please enter a URL.");

        urlInput.focus();

        return;
    }


    // Check URL

    let finalURL = url;

    if (
        !url.startsWith("http://") &&
        !url.startsWith("https://")
    ) {

        finalURL = "https://" + url;

    }


    // Create new link

    const newLink = {

        id: Date.now(),

        title: title,

        url: finalURL,

        category: category || "General",

        description: description || "No description",

        favorite: false

    };


    // Add to array

    links.push(newLink);


    // Refresh display

    renderLinks();


    // Clear inputs

    titleInput.value = "";
    urlInput.value = "";
    categoryInput.value = "";
    descriptionInput.value = "";


    alert("✅ Link added successfully!");

});


// ------------------------------------------
// Open Link
// ------------------------------------------

function openLink(url) {

    window.open(url, "_blank");

}


// ------------------------------------------
// Delete Link
// ------------------------------------------

function deleteLink(id) {

    const confirmDelete = confirm(
        "Are you sure you want to delete this link?"
    );


    if (!confirmDelete) {

        return;

    }


    links = links.filter(function(link) {

        return link.id !== id;

    });


    renderLinks();

}


// ------------------------------------------
// Favorite Link
// ------------------------------------------

function toggleFavorite(id) {

    const link = links.find(function(link) {

        return link.id === id;

    });


    if (!link) {

        return;

    }


    link.favorite = !link.favorite;


    renderLinks();

}


// ------------------------------------------
// Open Edit Modal
// ------------------------------------------

function openEditModal(id) {

    const link = links.find(function(link) {

        return link.id === id;

    });


    if (!link) {

        return;

    }


    editingLinkId = id;


    editTitle.value = link.title;

    editUrl.value = link.url;

    editCategory.value = link.category;

    editDescription.value = link.description;


    editModal.style.display = "flex";

}


// ------------------------------------------
// Close Edit Modal
// ------------------------------------------

closeModalBtn.addEventListener("click", function() {

    editModal.style.display = "none";

});


// Close modal by clicking outside

window.addEventListener("click", function(event) {

    if (event.target === editModal) {

        editModal.style.display = "none";

    }

});


// ------------------------------------------
// Save Edited Link
// ------------------------------------------

saveEditBtn.addEventListener("click", function() {

    if (editingLinkId === null) {

        return;

    }


    const link = links.find(function(link) {

        return link.id === editingLinkId;

    });


    if (!link) {

        return;

    }


    const newTitle = editTitle.value.trim();

    const newURL = editUrl.value.trim();

    const newCategory = editCategory.value.trim();

    const newDescription = editDescription.value.trim();


    if (newTitle === "") {

        alert("Title cannot be empty.");

        return;

    }


    if (newURL === "") {

        alert("URL cannot be empty.");

        return;

    }


    let finalURL = newURL;


    if (
        !newURL.startsWith("http://") &&
        !newURL.startsWith("https://")
    ) {

        finalURL = "https://" + newURL;

    }


    // Update link

    link.title = newTitle;

    link.url = finalURL;

    link.category = newCategory || "General";

    link.description = newDescription || "No description";


    // Close modal

    editModal.style.display = "none";


    editingLinkId = null;


    // Refresh

    renderLinks();


    alert("✅ Link updated successfully!");

});


// ------------------------------------------
// Search
// ------------------------------------------

searchInput.addEventListener("input", function() {

    const searchText = searchInput.value.toLowerCase().trim();


    const filteredLinks = links.filter(function(link) {

        return (

            link.title.toLowerCase().includes(searchText) ||

            link.url.toLowerCase().includes(searchText) ||

            link.category.toLowerCase().includes(searchText) ||

            link.description.toLowerCase().includes(searchText)

        );

    });


    renderLinks(filteredLinks);

});


// ------------------------------------------
// HTML Security
// ------------------------------------------

function escapeHTML(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

}


function escapeAttribute(text) {

    return text
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

}


// ------------------------------------------
// Initial Display
// ------------------------------------------

renderLinks();