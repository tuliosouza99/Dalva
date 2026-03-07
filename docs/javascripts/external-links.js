// Open external navigation links in new tab
document.addEventListener("DOMContentLoaded", function() {
  var links = document.querySelectorAll("nav a[href^='http']");

  links.forEach(function(link) {
    link.setAttribute("target", "_blank");
    link.setAttribute("rel", "noopener noreferrer");

    // Add external link icon
    var icon = document.createElement("span");
    icon.innerHTML = " ↗";
    link.appendChild(icon);
  });
});
