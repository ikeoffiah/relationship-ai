from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.personalization.models import UserProfile
from apps.personalization.serializers import UserProfileSerializer
from apps.personalization.tasks import compute_prompt_modifiers


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def post(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            compute_prompt_modifiers.delay(profile.id)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.post(request)


class QuestionnaireView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rsq_questions = [
            {"id": 1, "text": "I find it difficult to depend on other people."},
            {"id": 2, "text": "It is very important to me to feel independent."},
            {"id": 3, "text": "I find it easy to get emotionally close to others."},
            {"id": 4, "text": "I want to merge completely with another person."},
            {"id": 5, "text": "I worry that I will be hurt if I allow myself to become too close to others."},
            {"id": 6, "text": "I am comfortable without close emotional relationships."},
            {"id": 7, "text": "I am not sure that I can always depend on others to be there when I need them."},
            {"id": 8, "text": "I want to be completely emotionally intimate with others."},
            {"id": 9, "text": "I worry about being alone."},
            {"id": 10, "text": "I am comfortable depending on other people."},
            {"id": 11, "text": "I often worry that romantic partners don't really love me."},
            {"id": 12, "text": "I find it difficult to trust others completely."},
            {"id": 13, "text": "I worry about others getting too close to me."},
            {"id": 14, "text": "I want emotionally close relationships."},
            {"id": 15, "text": "I am comfortable having other people depend on me."},
            {"id": 16, "text": "I worry that others don't value me as much as I value them."},
            {"id": 17, "text": "People are never there when you need them."},
            {"id": 18, "text": "My desire to merge completely sometimes scares people away."},
            {"id": 19, "text": "It is very important to me to feel self-sufficient."},
            {"id": 20, "text": "I am nervous when anyone gets too close to me."},
            {"id": 21, "text": "I often worry that romantic partners won't want to stay with me."},
            {"id": 22, "text": "I prefer not to have other people depend on me."},
            {"id": 23, "text": "I worry about being abandoned."},
            {"id": 24, "text": "I am somewhat uncomfortable being close to others."},
            {"id": 25, "text": "I find that others are reluctant to get as close as I would like."},
            {"id": 26, "text": "I prefer not to depend on others."},
            {"id": 27, "text": "I know that others will be there when I need them."},
            {"id": 28, "text": "I worry about having others not accept me."},
            {"id": 29, "text": "Romantic partners often want me to be closer than I feel comfortable being."},
            {"id": 30, "text": "I find it relatively easy to get close to others."}
        ]

        stages = [
            {"id": "early_dating", "label": "Early Dating / Exploration"},
            {"id": "newlyweds", "label": "Newlyweds / Settling In"},
            {"id": "committed", "label": "Committed / Long-Term"},
            {"id": "crisis", "label": "Relationship Crisis / Conflict"},
            {"id": "post_infidelity", "label": "Post-Infidelity / Rebuilding Trust"},
            {"id": "separation_considering", "label": "Considering Separation"},
            {"id": "long_term", "label": "Long-Term / Rebuilding Intimacy"}
        ]

        communication_quiz = [
            {
                "id": 1,
                "question": "When you and your partner disagree on a major decision, you typically...",
                "options": [
                    {"value": "assertive", "text": "State your views clearly and propose a compromise."},
                    {"value": "passive", "text": "Go along with what they want to avoid conflict, even if unhappy."},
                    {"value": "analytical", "text": "Analyze the facts, pros, and cons logically to find the best solution."},
                    {"value": "expressive", "text": "Express your feelings with passion, tell stories or paint a picture of how you feel."},
                    {"value": "avoidant", "text": "Change the subject, walk away, or give short, distant answers."}
                ]
            },
            {
                "id": 2,
                "question": "When you feel hurt by something your partner said, you typically...",
                "options": [
                    {"value": "assertive", "text": "Explain how you feel using 'I' statements and ask for what you need."},
                    {"value": "passive", "text": "Say nothing and hope they notice, or apologize for causing tension."},
                    {"value": "analytical", "text": "Break down logically why the statement was incorrect or unfair."},
                    {"value": "expressive", "text": "React emotionally, using metaphors or expressive language to show your pain."},
                    {"value": "avoidant", "text": "Withdraw completely, stop responding, or avoid contact for a while."}
                ]
            },
            {
                "id": 3,
                "question": "When your partner is upset and needs emotional support, you...",
                "options": [
                    {"value": "assertive", "text": "Listen actively, validate their feelings, and ask how you can support them."},
                    {"value": "passive", "text": "Agree with whatever they say just to soothe them and keep the peace."},
                    {"value": "analytical", "text": "Offer practical advice, ask 'why' questions, and look for solutions."},
                    {"value": "expressive", "text": "Share a similar emotional experience or use rich stories to connect with them."},
                    {"value": "avoidant", "text": "Feel overwhelmed, change the topic, or excuse yourself to give them space."}
                ]
            },
            {
                "id": 4,
                "question": "When discussing future plans (like moving, finances, or career), you prefer to...",
                "options": [
                    {"value": "assertive", "text": "Express your goals directly while inviting them to share theirs openly."},
                    {"value": "passive", "text": "Let them make the decisions and adapt yourself to whatever they choose."},
                    {"value": "analytical", "text": "Analyze research, spreadsheets, and evidence-based options together."},
                    {"value": "expressive", "text": "Discuss your dreams, feelings, and the overall vision for your life together."},
                    {"value": "avoidant", "text": "Postpone the discussion or keep your responses short and non-committal."}
                ]
            },
            {
                "id": 5,
                "question": "In the middle of a heated argument, your first instinct is to...",
                "options": [
                    {"value": "assertive", "text": "Suggest a brief pause to cool down, then return to talk it out calmly."},
                    {"value": "passive", "text": "Give in immediately, apologizing just to make the argument stop."},
                    {"value": "analytical", "text": "Request that both of you stick strictly to the facts and objective points."},
                    {"value": "expressive", "text": "Use intense language, raise your voice, or express your feelings dramatically."},
                    {"value": "avoidant", "text": "Shut down, stop talking, or physically leave the room."}
                ]
            }
        ]

        return Response({
            "rsq_questions": rsq_questions,
            "stages": stages,
            "communication_quiz": communication_quiz
        })
