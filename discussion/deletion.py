"""
Inspired from: https://www.django-antipatterns.com/pattern/a-set-delete-handler-with-the-object-as-parameter.html
"""

from django.db.models.deletion import CASCADE

DO_CASCADE = object()  # Serves as a flag to indicate that the related object should be deleted


def SET_WITH(func):
    """
    Given a function that takes the related object of the object to delete as parameter, this will replace the object
    to delete with the result of the function. If the function returns DO_CASCADE, the related object will be deleted.

    :param func: Function that takes the related object of the object to delete as parameter
    :return: Function that will replace the object to delete with the result of the function
    """
    def set_on_delete(collector, field, sub_objs, using):
        cascades = []  # Objects that should be deleted
        for obj in sub_objs:  # List of objects that are related to the object to delete (might be indirect)
            result = func(obj)  # Call the function with the object to delete as parameter
            if result is DO_CASCADE:
                # If the result is DO_CASCADE, add the object to the cascades list
                cascades.append(obj)
            else:
                # If the result is not DO_CASCADE, add the result (replacing the object) to field_updates
                collector.add_field_update(field, result, [obj])
        if cascades:  # If there are objects to delete, delete them
            CASCADE(collector, field, cascades, using)

    set_on_delete.deconstruct = lambda: ('discussion.SET_WITH', (func,), {})
    return set_on_delete
