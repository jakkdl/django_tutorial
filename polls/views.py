from django.db.models import F
from django.db.models import QuerySet
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import generic

from .models import Choice
from .models import Question


class IndexView(generic.ListView[Question]):
    template_name = "polls/index.html"
    context_object_name = "latest_questions"

    def get_queryset(self) -> QuerySet[Question]:
        """return the last five published queries"""
        return Question.objects.filter(pub_date__lte=timezone.now()).order_by(
            "-pub_date"
        )[:5]


class DetailView(generic.DetailView[Question]):
    model = Question
    template_name = "polls/detail.html"

    def get_queryset(self) -> QuerySet[Question]:
        return Question.objects.filter(pub_date__lte=timezone.now())


class ResultsView(generic.DetailView[Question]):
    model = Question
    template_name = "polls/results.html"


def vote(request: HttpRequest, question_id: int) -> HttpResponse:
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        return render(
            request,
            "polls/detail.html",
            {"question": question, "error_message_vote": "Please select a choice"},
        )
    selected_choice.votes = F("votes") + 1
    selected_choice.save()
    # return a HttpResponseRedirect to prevent data being posted twice if user hits back
    return HttpResponseRedirect(reverse("results", args=(question.id,)))


def add_choice(request: HttpRequest, question_id: int) -> HttpResponse:
    question = get_object_or_404(Question, pk=question_id)
    choice_text = request.POST["choice_text"]
    choice_votes = request.POST["choice_votes"]
    if not choice_text:
        return render(
            request,
            "polls/detail.html",
            {"question": question, "error_message_add": "Please enter a choice text"},
        )
    Choice.objects.create(
        question=question, choice_text=choice_text, votes=choice_votes
    )
    return HttpResponseRedirect(reverse("results", args=(question.id,)))
