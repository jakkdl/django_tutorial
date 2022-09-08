from datetime import timedelta

import pytest
from django.http.response import Http404
from django.http.response import HttpResponseRedirect
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Choice
from .models import Question
from .views import add_choice
from .views import vote


class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self) -> None:
        time = timezone.now() + timedelta(days=30)
        future_question = Question(pub_date=time)
        assert not future_question.was_published_recently()

    def test_was_published_recently_with_old_question(self) -> None:
        time = timezone.now() - timedelta(days=1)
        future_question = Question(pub_date=time)
        assert not future_question.was_published_recently()

    def test_was_published_recently_with_recent_question(self) -> None:
        time = timezone.now() - timedelta(hours=23, minutes=59, seconds=59)
        future_question = Question(pub_date=time)
        assert future_question.was_published_recently()


def create_question(question_text: str, days: int) -> Question:
    time = timezone.now() + timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


class QuestionIndexViewTests(TestCase):
    def test_no_questions(self) -> None:
        response = self.client.get(reverse("index"))
        assert response.status_code == 200
        self.assertContains(response, "No polls are available.")
        self.assertSequenceEqual(response.context["latest_questions"], [])

    def test_past_question(self) -> None:
        """
        Questions with a pub_date in the past are displayed on the
        index page.
        """
        question = create_question(question_text="Past question.", days=-30)
        response = self.client.get(reverse("index"))
        self.assertSequenceEqual(
            response.context["latest_questions"],
            [question],
        )

    def test_future_question(self) -> None:
        """
        Questions with a pub_date in the future aren't displayed on
        the index page.
        """
        create_question(question_text="Future question.", days=30)
        self.test_no_questions()

    def test_future_question_and_past_question(self) -> None:
        """
        Even if both past and future questions exist, only past questions
        are displayed.
        """
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("index"))
        self.assertSequenceEqual(
            response.context["latest_questions"],
            [question],
        )

    def test_two_past_questions(self) -> None:
        """
        The questions index page may display multiple questions.
        """
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse("index"))
        self.assertSequenceEqual(
            response.context["latest_questions"],
            [question2, question1],
        )


class QuestionDetailViewTests(TestCase):
    def test_future_question(self) -> None:
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("detail", args=(future_question.id,))
        response = self.client.get(url)
        assert response.status_code == 404

    def test_past_question(self) -> None:
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(question_text="Past Question.", days=-5)
        url = reverse("detail", args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)

    def test_question(self) -> None:
        question = create_question(question_text="MyQuestion", days=0)
        choice1 = Choice.objects.create(question=question, choice_text="MyChoice1")
        assert "MyQuestion" in str(choice1)
        assert "MyChoice1" in str(choice1)

    def test_vote(self) -> None:
        """create a question, add choices to it, vote on one of them"""
        question = create_question(question_text="MyQuestion", days=0)
        choice1 = Choice.objects.create(question=question, choice_text="MyChoice1")
        choice1.save()
        request = RequestFactory().post("polls/vote", {"choice": choice1.pk})
        response = vote(request, question.pk)

        # check response
        assert response.status_code == 302
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == "/1/results/"

        # check votes
        assert Choice.objects.get(pk=choice1.pk).votes == 1
        choice1.refresh_from_db()
        assert choice1.votes == 1

    def test_vote_no_question(self) -> None:
        request = RequestFactory().post("polls/vote", {"choice": 1})
        with pytest.raises(Http404):
            vote(request, 1)

    def test_vote_invalid_choice(self) -> None:
        question = create_question(question_text="MyQuestion", days=0)
        request = RequestFactory().post("polls/vote", {"choice": 1})
        response = vote(request, question.pk)
        self.assertContains(response, "Please select a choice")

    def test_add_choice(self) -> None:
        question = create_question(question_text="MyQuestion", days=0)
        request = RequestFactory().post(
            "polls/add_choice", {"choice_text": "my_choice", "choice_votes": 2}
        )
        add_choice(request, question.pk)
        assert Choice.objects.filter(choice_text="my_choice")

    def test_add_empty_choice(self) -> None:
        question = create_question(question_text="MyQuestion", days=0)
        request = RequestFactory().post(
            "polls/add_choice", {"choice_text": "", "choice_votes": 2}
        )
        response = add_choice(request, question.pk)
        self.assertContains(response, "Please enter a choice text")
