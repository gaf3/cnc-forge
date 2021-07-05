(function () {
  console.log("HELLO");
  gsap.from("text,#flame", { x: -100, stagger: 0.05, duration: 0.5 });
  gsap.from("#main-subtitle", { opacity: 0, delay: 1.25 });
})();
