window.onload = function () {
    const rollingBox = document.getElementById("rolling");
    if (!rollingBox) return;

    const names = document.querySelectorAll(".player-item");
    let index = 0;

    const timer = setInterval(() => {
        rollingBox.innerText = names[index].innerText;
        index = (index + 1) % names.length;
    }, 100);

    setTimeout(() => {
        clearInterval(timer);
        document.getElementById("final-winner").style.display = "block";
    }, 3000);
};