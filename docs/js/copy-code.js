document.addEventListener('DOMContentLoaded', function() {
  // Find all code blocks
  const codeBlocks = document.querySelectorAll('pre');
  
  codeBlocks.forEach(block => {
    // Create copy button
    const button = document.createElement('button');
    button.className = 'copy-code-btn';
    button.innerHTML = '📋 Copy';
    button.type = 'button';
    
    // Add click handler
    button.addEventListener('click', function() {
      const code = block.querySelector('code');
      const text = code ? code.textContent : block.textContent;
      
      navigator.clipboard.writeText(text).then(function() {
        // Feedback on success
        const originalText = button.innerHTML;
        button.innerHTML = '✓ Copied!';
        button.classList.add('copied');
        
        setTimeout(function() {
          button.innerHTML = originalText;
          button.classList.remove('copied');
        }, 2000);
      }).catch(function(err) {
        console.error('Failed to copy: ', err);
      });
    });
    
    // Add button to block
    block.style.position = 'relative';
    block.appendChild(button);
  });
});
