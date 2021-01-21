(function () {
  console.log("HELLO");
  gsap.from("text,#flame", { x: -100, stagger: 0.05 }, 250);
  gsap.from("#main-subtitle", { opacity: 0 }, 1000);
})();
