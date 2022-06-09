import json
import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10


def paginate_questions(request, data):
    # Get the page parameter from the request url
    page = request.args.get("page", 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [question.format() for question in data]
    current_questions = questions[start:end]

    return current_questions

def randomize(start, end):
    return random.randrange(start, end)


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)

    CORS(app)

    @app.after_request
    def after_request(response):
        response.headers.add(
            "Access-Control-Allow-Headers", "Content-Type,Authorization,true"
        )
        response.headers.add(
            "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS"
        )
        return response

    """
    Create an endpoint to handle GET requests for all available categories.
    """
    @app.route("/categories")
    def retrieve_categories():
        # Get all the categories
        categories = Category.query.order_by(Category.type).all()

        if len(categories) == 0:
            abort(404)

        return jsonify(
            {
                "success": True,
                "categories": {
                    category.id: category.type for category in categories
                },
                "total_categories": len(Category.query.all())
            }
        )

    """
    Create an endpoint to handle GET requests for questions,
    including pagination (every 10 questions).
    """
    @app.route("/questions")
    def retrieve_questions():
        # Get all the questions
        data = Question.query.order_by(Question.id).all()

        # Get 10 questions per page
        current_questions = paginate_questions(request, data)

        categories = Category.query.order_by(Category.type).all()

        if len(current_questions) == 0:
            abort(400)

        return jsonify({
            "success": True,
            "questions": current_questions,
            "total_questions": len(Question.query.all()),
            "categories": {
                category.id: category.type for category in categories
            },
            "current_category": None,
        })

    """
    Create an endpoint to DELETE question using a question ID.
    """
    @app.route("/questions/<int:question_id>", methods=["DELETE"])
    def delete_question(question_id):
        try:
            # Get the question whose id matches that of the question to be deleted
            question = Question.query.filter(
                Question.id == question_id).one_or_none()

            # If the question does not exist:
            if question is None:
                abort(404)

            question.delete()

            # Get the remaining questions
            data = Question.query.order_by(Question.id).all()
            current_questions = paginate_questions(request, data)

            return jsonify(
                {
                    "success": True,
                    "deleted": question_id,
                    "questions": current_questions,
                    "total_questions": len(Question.query.all())
                }
            )

        except:
            abort(422)
    """
    Create an endpoint to POST a new question,
    which will require the question and answer text,
    category, and difficulty score.
    """
    @app.route("/questions", methods=["POST"])
    def create_question():
        # Get the json request data
        body = request.get_json()

        new_question = body.get("question", None)
        new_answer = body.get("answer", None)
        new_difficulty = body.get("difficulty", None)
        new_category = body.get("category", None)

        try:
            # Create a new question from the data gotten from the request
            question = Question(question=new_question, answer=new_answer,
                                category=new_category, difficulty=new_difficulty)
            question.insert()

            data = Question.query.order_by(Question.id).all()
            current_questions = paginate_questions(request, data)

            return jsonify({
                "success": True,
                "created": question.id,
                "questions": current_questions,
                "total_questions": len(Question.query.all())
            })

        except:
            abort(422)

    """
    Create a POST endpoint to get questions based on a search term.
    """
    @app.route("/questions/search", methods=["POST"])
    def search_questions():
        # Get the search term from the json request data
        search_term = request.get_json().get('searchTerm')

        if search_term:
            # Get all the questions that match the search term (case-insensitive)
            results = Question.query.filter(
                Question.question.ilike(f'%{search_term}%')).all()

            return jsonify({
                "success": True,
                "questions": [result.format() for result in results],
                "total_questions": len(results),
                "current_category": None
            })

        abort(404)

    """
    Create a GET endpoint to get questions based on category.
    """
    @app.route("/categories/<int:category_id>/questions")
    def retrieve_questions_by_category(category_id):
        # Get the questions whose categories are equal to the specified category
        questions = Question.query.filter(
            Question.category == category_id).all()

        if len(questions) == 0:
            abort(404)

        return jsonify({
            "success": True,
            "questions": [question.format() for question in questions],
            "total_questions": len(questions),
            "current_category": category_id
        })

    """
    Create a POST endpoint to get questions to play the quiz.
    This endpoint should take category and previous question parameters
    and return a random questions within the given category,
    if provided, and that is not one of the previous questions.
    """
    @app.route("/quizzes", methods=["POST"])
    def start_quiz():
        try:
            if not 'quiz_category' in request.get_json() and not 'previous_questions' in request.get_json():
                abort(422)

            category = request.get_json().get('quiz_category')
            quiz_category_id = category['id']
            asked_questions = request.get_json().get('previous_questions')

            # If the category is all:
            if quiz_category_id == 0:
                free_questions = Question.query.filter(
                    Question.id.notin_(asked_questions)).all()
            else:
            # Get the questions that are not in previous_questions i.e have not been asked already and whose category match the category from the request
                free_questions = Question.query.filter_by(category=quiz_category_id).filter(
                    Question.id.notin_(asked_questions)
                ).all()

            num_questions = len(free_questions)
            if num_questions < 0:
                current_question = None
            else:
                current_question = free_questions[randomize(
                    0, num_questions)].format()

            return jsonify({
                "success": True,
                "question": current_question
            })

        except BaseException:
            abort(422)

    """
    Create error handlers for all expected errors
    including 404 and 422.
    """
    @app.errorhandler(404)
    def not_found(error):
        return (
            jsonify({
                "success": False,
                "error": 404,
                "message": "Resource not found"
            }),
            404
        )

    @app.errorhandler(400)
    def bad_request(error):
        return (
            jsonify({
                "success": False,
                "error": 400,
                "message": "Bad request. Please try again"
            }),
            400
        )

    @app.errorhandler(422)
    def unprocessable(error):
        return (
            jsonify({
                "success": False,
                "error": 422,
                "message": "Request was unprocessable"
            }),
            422
        )
    return app
