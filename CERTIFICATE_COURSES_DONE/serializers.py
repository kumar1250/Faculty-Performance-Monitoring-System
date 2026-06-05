from rest_framework import serializers

from .models import Course
class CourseSerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files are 'jpg', 'jpeg', 'png', 'gif', 'webp' allowed."
            )

        return value
    class Meta:
        model = Course
        fields = '__all__'
        

class CreateCourseSerializer(serializers.ModelSerializer):
    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif','webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files are 'jpg', 'jpeg', 'png', 'gif', 'webp' allowed."
            )

        return value

    class Meta:
        model = Course
        fields = ['id','user', 'certificate_type', 'Course_name', 'certificate_file']
