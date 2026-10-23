import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMyInterests, updateMyInterests } from '../api';
import { useToast } from '../components/Toast';
import { ArrowRight, Check } from 'lucide-react';
import { categoryIcon } from '../utils/icons';
import './OnboardingPage.css';

/**
 * Onboarding categories strictly mapped to actual database categories and tags.
 * "Innovation" is merged into Career & Innovation to maintain 1-to-1 consistency with feed chips.
 */
const ONBOARDING_CATEGORIES = [
  {
    id: 'Tech',
    name: 'Tech & Coding',
    subtitle: 'Python, AI, Cloud, Cybersecurity',
    tags: ['tech', 'python', 'web development', 'ai', 'cloud', 'data science', 'iot', 'cybersecurity'],
  },
  {
    id: 'Academic',
    name: 'Academic & Research',
    subtitle: 'Science, Research, Seminars, Thesis',
    tags: ['academic', 'science', 'research', 'seminar', 'lecture', 'mathematics', 'thesis'],
  },
  {
    id: 'Career',
    name: 'Career & Innovation',
    subtitle: 'Startups, Internships, Mentorship',
    tags: ['career', 'interview', 'mentorship', 'leadership', 'startup', 'networking', 'skills', 'entrepreneurship', 'internship'],
  },
  {
    id: 'Social',
    name: 'Social & Campus Life',
    subtitle: 'Mixers, Games, Networking, Parties',
    tags: ['social', 'community', 'games', 'networking', 'mixer', 'party', 'picnic', 'karaoke'],
  },
  {
    id: 'Sports',
    name: 'Sports & Fitness',
    subtitle: 'Athletics, Fitness, Tournaments',
    tags: ['sports', 'fitness', 'athletics', 'marathon', 'swimming', 'football', 'basketball'],
  },
  {
    id: 'Workshop',
    name: 'Workshops & Practical',
    subtitle: 'Hands-on Training, Bootcamps',
    tags: ['workshop', 'hands-on', 'training', 'skills', 'bootcamp'],
  },
  {
    id: 'Cultural',
    name: 'Arts & Culture',
    subtitle: 'Music, Heritage, Film, Poetry',
    tags: ['cultural', 'art', 'heritage', 'music', 'community', 'dance', 'film', 'poetry', 'theatre'],
  },
];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const toast = useToast();

  const [selectedCategoryIds, setSelectedCategoryIds] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Load existing interests if user already has some
  useEffect(() => {
    async function loadCurrentInterests() {
      try {
        const existing = await getMyInterests();
        if (existing && existing.length > 0) {
          setIsEditing(true);
          const existingTags = new Set(existing.map((item) => item.interest_tag.toLowerCase()));
          const preSelected = new Set();
          
          ONBOARDING_CATEGORIES.forEach((cat) => {
            const hasMatch = cat.tags.some((t) => existingTags.has(t.toLowerCase())) || existingTags.has(cat.id.toLowerCase());
            if (hasMatch) {
              preSelected.add(cat.id);
            }
          });

          if (preSelected.size > 0) {
            setSelectedCategoryIds(preSelected);
          }
        }
      } catch {
        // Non-blocking
      }
    }
    loadCurrentInterests();
  }, []);

  function toggleCategory(catId) {
    setSelectedCategoryIds((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) {
        next.delete(catId);
      } else {
        next.add(catId);
      }
      return next;
    });
  }

  const selectedCount = selectedCategoryIds.size;
  const isComplete = selectedCount >= 3;
  const remainingNeeded = Math.max(0, 3 - selectedCount);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!isComplete) {
      toast.error('Please pick at least 3 categories so we can personalize your feed.');
      return;
    }

    setLoading(true);
    try {
      // Collect tags from all selected categories
      const allTagsToSave = new Set();
      selectedCategoryIds.forEach((catId) => {
        const cat = ONBOARDING_CATEGORIES.find((c) => c.id === catId);
        if (cat) {
          allTagsToSave.add(cat.id.toLowerCase());
          cat.tags.forEach((t) => allTagsToSave.add(t.toLowerCase()));
        }
      });

      const payload = Array.from(allTagsToSave).map((tag) => ({
        tag,
        weight: 1.0,
      }));

      await updateMyInterests(payload);
      toast.success(isEditing ? 'Interests updated! Feed refreshed.' : 'Feed personalized! Welcome to Tukio.');
      navigate('/events');
    } catch (err) {
      toast.error(err.message || 'Failed to save interests. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="tukio-onboarding-page">
      <div className="tukio-onboarding-card animate-fade-in">
        {/* Header */}
        <div className="tukio-onboarding-header">
          <span className="tukio-onboarding-badge">
            {isEditing ? 'Update Preferences' : 'Quick Onboarding'}
          </span>
          <h1 className="tukio-onboarding-title">
            {isEditing ? 'Tune Your Tukio Feed' : 'Personalize Your Feed'}
          </h1>
          <p className="tukio-onboarding-subtitle">
            Pick <strong>3 or more</strong> categories so our recommendation engine can curate events matching your campus journey.
          </p>
        </div>

        {/* Live Requirement Tracker */}
        <div className={`tukio-onboarding-tracker ${isComplete ? 'complete' : 'incomplete'}`}>
          {isComplete
            ? `Ready to explore (${selectedCount} selected)`
            : `Pick at least 3 categories (${remainingNeeded} more needed)`}
        </div>

        {/* Category Tiles Grid with accessible buttons */}
        <form onSubmit={handleSubmit}>
          <div className="tukio-onboarding-grid" role="group" aria-label="Campus event interest categories">
            {ONBOARDING_CATEGORIES.map((category) => {
              const isSelected = selectedCategoryIds.has(category.id);
              const TileIcon = categoryIcon(category.id);
              return (
                <button
                  key={category.id}
                  type="button"
                  className={`tukio-onboarding-tile ${isSelected ? 'selected' : ''}`}
                  onClick={() => toggleCategory(category.id)}
                  aria-pressed={isSelected}
                >
                  <div className="tukio-tile-top">
                    <span className="tukio-tile-emoji" aria-hidden="true">
                      <TileIcon size={32} strokeWidth={1.75} />
                    </span>
                    <span className="tukio-tile-check" aria-hidden="true">{isSelected ? <Check size={14} /> : null}</span>
                  </div>
                  <h3 className="tukio-tile-label">{category.name}</h3>
                  <span className="tukio-tile-sub">{category.subtitle}</span>
                </button>
              );
            })}
          </div>

          {/* Action CTAs */}
          <div className="tukio-onboarding-actions">
            <button
              type="submit"
              className="tukio-onboarding-submit-btn"
              disabled={!isComplete || loading}
            >
              {loading ? (
                <span className="tukio-micro-spinner" />
              ) : isEditing ? (
                <>Save and update feed <ArrowRight size={16} aria-hidden="true" /></>
              ) : (
                <>Personalize my feed <ArrowRight size={16} aria-hidden="true" /></>
              )}
            </button>

            <button
              type="button"
              className="tukio-onboarding-skip-btn"
              onClick={() => navigate('/events')}
            >
              Skip for now <ArrowRight size={14} aria-hidden="true" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
