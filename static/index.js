// Event listener for the form submission (to fetch images from Reddit)
document.getElementById('redditForm').addEventListener('submit', async function(event) {
    event.preventDefault();  // Prevent the default form submission behavior (page reload)
    
    // Get the URL entered by the user
    const postUrl = document.getElementById('postUrl').value;
    
    // Get references to the loader, results, and download button elements
    const loader = document.getElementById('loader');
    const resultsDiv = document.getElementById('results');
    const downloadBtn = document.getElementById('downloadBtn');

    loader.style.display = 'block';  // Show the loader (indicating that the request is processing)
    resultsDiv.innerHTML = ''; // Clear previous results displayed on the page

    // Send an authentication request to the server to get an access token
    const response = await fetch('/auth', {
        method: 'POST',  // Send the POST request
    });
    const data = await response.json();  // Parse the JSON response
    const token = data.token;  // Extract the token from the response

    // Now that we have the token, fetch images from the Reddit post
    const fetchResponse = await fetch('/fetch-images', {
        method: 'POST',  // Send the POST request to fetch images
        headers: {
            'Content-Type': 'application/json',  // Inform server that we're sending JSON data
        },
        body: JSON.stringify({ token, url: postUrl }),  // Send the token and Reddit post URL in the request body
    });

    const result = await fetchResponse.json();  // Parse the response from the server
    loader.style.display = 'none'; // Hide the loader after the process is done

    // Check if the server returned images in the response
    if (result.images) {
        // Loop through each image URL and display it on the page
        result.images.forEach(imageUrl => {
            const imgElement = document.createElement('img');  // Create a new <img> element
            imgElement.src = imageUrl;  // Set the image source to the URL received
            resultsDiv.appendChild(imgElement);  // Append the image element to the results div
        });
        downloadBtn.style.display = 'inline-block'; // Make the download button visible once images are displayed
    } else {
        // If no images are found, display an error message
        resultsDiv.innerHTML = 'No images found or error occurred.';
    }
});

// Event listener for the "Download Images" button
document.getElementById('downloadBtn').addEventListener('click', async function() {
    // Get references to the loader and results elements
    const loader = document.getElementById('loader');
    const resultsDiv = document.getElementById('results');
    
    loader.style.display = 'block'; // Show the loader while the images are being prepared for download
    resultsDiv.innerHTML = ''; // Clear any previous results in the results div
    
    // Send a request to the server to download all the images as a ZIP file
    const response = await fetch('/download-images', {
        method: 'POST',  // Send the POST request to the server
    });
    
    // Check if the response was successful
    if (response.ok) {
        // Convert the response to a Blob (binary large object) representing the ZIP file
        const blob = await response.blob();
        
        // Create an invisible <a> element to trigger the download
        const downloadLink = document.createElement('a');
        downloadLink.href = URL.createObjectURL(blob);  // Set the href attribute to the Blob URL
        downloadLink.download = 'reddit_images.zip';  // Specify the default filename for the download
        downloadLink.click();  // Simulate a click on the <a> element to start the download
        loader.style.display = 'none'; // Hide the loader after the download has started
    } else {
        // If the download fails, display an error message
        resultsDiv.innerHTML = 'Error downloading images.';
        loader.style.display = 'none'; // Hide the loader after the error is displayed
    }
});
