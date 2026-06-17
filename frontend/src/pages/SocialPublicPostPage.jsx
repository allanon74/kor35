import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { socialGetPublicPostBySlug, resolveMediaUrl } from '../api';
import InstafameMediaCarousel from '../components/InstafameMediaCarousel';
import { formatCount } from '../utils/formatCount';

export default function SocialPublicPostPage() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await socialGetPublicPostBySlug(slug);
        if (mounted) setPost(data);
      } catch (e) {
        if (mounted) setError('Post non trovato o non pubblico.');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [slug]);

  if (loading) return <div className="p-8 text-center text-gray-500">Caricamento post...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!post) return null;

  const postImages =
    Array.isArray(post.immagini) && post.immagini.length > 0
      ? post.immagini
      : post.immagine
        ? [post.immagine]
        : [];

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-8">
      <div className="bg-white rounded-xl shadow border border-gray-200 overflow-hidden">
        <div className="px-5 pt-5 pb-3">
          <p className="text-sm text-gray-500">
            <span className="font-semibold text-gray-900">{post.autore_nome}</span>
            {' · '}
            {new Date(post.created_at).toLocaleString('it-IT')}
          </p>
        </div>

        {postImages.length > 0 && (
          <InstafameMediaCarousel images={postImages} alt={post.titolo} fullWidth className="border-gray-200" />
        )}
        {post.video && (
          <div className="w-full aspect-4/5 overflow-hidden border-y border-gray-200 bg-black">
            <video controls src={resolveMediaUrl(post.video)} className="h-full w-full object-cover" />
          </div>
        )}

        <div className="px-5 py-4 space-y-3">
          {post.titolo && <h1 className="text-xl md:text-2xl font-bold text-gray-900">{post.titolo}</h1>}
          {post.testo && <p className="text-gray-800 whitespace-pre-wrap">{post.testo}</p>}

          <div className="text-sm text-gray-600 border-t border-gray-200 pt-3">
            Like: <span className="font-semibold">{formatCount(post.likes_count)}</span> · Commenti:{' '}
            <span className="font-semibold">{formatCount(post.comments_count)}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 text-center">
        <Link to="/app/social" className="text-indigo-600 hover:text-indigo-500 font-semibold">
          Apri InstaFame
        </Link>
      </div>
    </div>
  );
}
