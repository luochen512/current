# -*- coding: utf-8 -*-
from django.utils import timezone


def dbdatetime_timedelta(timea, timeb):
    a = timea if timezone.is_naive(timea) else timezone.make_naive(timea)
    b = timeb if timezone.is_naive(timeb) else timezone.make_naive(timeb)
    return a - b

def to_naive(timea):
    return timea if timezone.is_naive(timea) else timezone.make_naive(timea)