// for bootStrap popover
const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]')
const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl))


// header stuck
$(window).scroll(function(){
	if($(this).scrollTop() > 70){
		$('#header').addClass("stickyHeader");
	} else{
        $('#header').removeClass("stickyHeader");
	}
});

const faqQuestions = document.querySelectorAll('.faq-question');

faqQuestions.forEach(question => {
	question.addEventListener('click', () => {
		const answer = question.nextElementSibling;
		question.classList.toggle('active');
		answer.classList.toggle('active');
	});
});